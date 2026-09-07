import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domain.scheduling.service import create_event
from app.domain.scheduling.models import ScheduledEvent
from app.main import create_app # to register mappers

# Requires a real database to test pg_advisory_xact_lock
# Assuming the test suite has access to the test database specified in DATABASE_URL

@pytest.mark.asyncio
async def test_concurrent_booking_prevents_overlap():
    from app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    workspace_id = uuid4()
    assigned_to = uuid4()
    target_time = datetime(2027, 10, 10, 14, 0, tzinfo=timezone.utc)
    
    # We will simulate two concurrent requests to create an event for the same assignee at the same time
    
    class MockRequest:
        def __init__(self):
            self.workspace_id = workspace_id
            self.customer_id = uuid4()
            self.conversation_id = uuid4()
            self.event_type = "meeting"
            self.title = "Test Meeting"
            self.description = "Test"
            self.priority = "medium"
            self.scheduled_for = target_time
            self.duration_minutes = 30
            self.assignment_strategy = "manual"
            self.assigned_to = assigned_to
            self.metadata = {}
    
    req1 = MockRequest()
    req2 = MockRequest()
    
    async def run_create(req):
        async with async_session() as session:
            try:
                # Need to run in a transaction for xact_lock to work
                async with session.begin():
                    event = await create_event(session, req, actor_id=uuid4(), actor_type="customer", is_demo=False)
                    return event, None
            except Exception as e:
                return None, e
                
    # Run concurrently
    results = await asyncio.gather(run_create(req1), run_create(req2))
    
    successes = 0
    failures = 0
    
    for event, err in results:
        if event:
            successes += 1
        elif err and "Double booking detected" in str(err):
            failures += 1
        else:
            print("OTHER ERROR:", err)
            
    assert successes == 1
    assert failures == 1
    
    await engine.dispose()
