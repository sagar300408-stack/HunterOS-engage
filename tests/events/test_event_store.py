import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domain.conversations.models import Base
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory
from app.domain.dashboard.models import PipelineEvent
from app.domain.security.models import AuditLog
from app.domain.followup.models import FollowUpQueue, FollowUpExecution, LeadHealthScore, SalesMemoryTimeline
from app.domain.memory.models import CustomerMemory
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.model.actor_types import ActorType
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService

# Use an in-memory SQLite database for fast async testing
@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(EventRecord.__table__.create)
        
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_persist_and_retrieve_event(async_session):
    repo = EventStoreRepository()
    service = EventStoreService(repository=repo)
    
    workspace_id = uuid.uuid4()
    
    event = CustomerRepliedEvent(
        workspace_id=workspace_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="test_suite",
        message_content="Hello, testing event store.",
        wa_message_id="wa_123"
    )
    
    await service.persist_event(async_session, event)
    
    # Retrieve the event
    events = await repo.get_events(async_session, workspace_id=workspace_id)
    assert len(events) == 1
    
    record = events[0]
    assert record.event_id == event.event_id
    assert record.workspace_id == workspace_id
    assert record.actor_type == "customer"
    assert record.category == "CONVERSATION"
    assert record.event_name == "customer.replied"
    assert record.payload["message_content"] == "Hello, testing event store."
