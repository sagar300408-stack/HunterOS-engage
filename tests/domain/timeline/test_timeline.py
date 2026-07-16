import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domain.conversations.models import Base
# Import everything to ensure mapper sees everything
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory
from app.domain.dashboard.models import PipelineEvent, AuditLog
from app.domain.followup.models import FollowUpQueue, FollowUpExecution, LeadHealthScore, SalesMemoryTimeline
from app.domain.memory.models import CustomerMemory
from app.domain.timeline.models import TimelineEntry, TimelineSeverity
from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.schemas import TimelineEntryResponse
from app.domain.timeline.service import TimelineProjection, TimelineQueryService
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.categories.scheduling_events import MeetingBookedEvent
from app.events.model.actor_types import ActorType


@pytest.fixture
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture
def session_maker(engine):
    return sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def async_session(engine, session_maker):
    async with engine.begin() as conn:
        # We only create timeline entry for test
        await conn.run_sync(TimelineEntry.__table__.create)
    
    async with session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_timeline_projection_customer_reply(async_session):
    repo = TimelineRepository()
    engine = TimelineProjection(repo)
    query_svc = TimelineQueryService(repo)
    
    workspace_id = uuid.uuid4()
    
    event = CustomerRepliedEvent(
        workspace_id=workspace_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="test",
        message_content="Yes, I am interested.",
        wa_message_id="msg_123"
    )
    
    # Process event
    entry = await engine.project_event(event, async_session)
    
    assert entry is not None
    assert entry.event_id == event.event_id
    assert entry.severity == TimelineSeverity.NORMAL
    assert entry.activity_type == "customer_replied"
    assert "snippet" in entry.structured_data
    assert entry.structured_data["snippet"] == "Yes, I am interested."
    
    # Query it back
    timeline = await query_svc.get_workspace_timeline(async_session, workspace_id)
    assert len(timeline) == 1
    
    response = timeline[0]
    assert isinstance(response, TimelineEntryResponse)
    assert response.activity_title == "Customer replied to conversation"
    assert response.activity_description == "Yes, I am interested."


@pytest.mark.asyncio
async def test_timeline_projection_meeting_booked(async_session):
    repo = TimelineRepository()
    engine = TimelineProjection(repo)
    query_svc = TimelineQueryService(repo)
    
    workspace_id = uuid.uuid4()
    meeting_time = datetime.now(timezone.utc).isoformat()
    
    event = MeetingBookedEvent(
        workspace_id=workspace_id,
        actor_type=ActorType.SYSTEM,
        source_subsystem="test",
        meeting_time=meeting_time,
        meeting_url="https://zoom.us/j/123",
        duration_minutes=30
    )
    
    await engine.project_event(event, async_session)
    
    timeline = await query_svc.get_workspace_timeline(async_session, workspace_id)
    assert len(timeline) == 1
    assert timeline[0].severity == TimelineSeverity.HIGH
    assert timeline[0].activity_title == "Meeting scheduled"
    assert meeting_time in timeline[0].activity_description
