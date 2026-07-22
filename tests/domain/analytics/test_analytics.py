import uuid
from datetime import datetime, timezone, date

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
from app.domain.timeline.models import TimelineEntry, TimelineSeverity

from app.domain.analytics.models import AnalyticsDailyMetric, AnalyticsMetricType
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.service import AnalyticsProjection, AnalyticsQueryService
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
        # We only create AnalyticsDailyMetric table for test
        await conn.run_sync(AnalyticsDailyMetric.__table__.create)
    
    async with session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_analytics_projection_increments(async_session):
    repo = AnalyticsRepository()
    projection = AnalyticsProjection(repo)
    query_svc = AnalyticsQueryService(repo)
    
    workspace_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    
    event1 = CustomerRepliedEvent(
        workspace_id=workspace_id,
        customer_id=customer_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="test",
        message_content="Yes",
        wa_message_id="msg_1"
    )
    
    event2 = CustomerRepliedEvent(
        workspace_id=workspace_id,
        customer_id=customer_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="test",
        message_content="No",
        wa_message_id="msg_2"
    )
    
    # Process both events
    await projection.project_event(event1, async_session)
    await projection.project_event(event2, async_session)
    
    # Check workspace metrics
    workspace_metrics = await query_svc.get_workspace_metrics(async_session, workspace_id)
    assert len(workspace_metrics) == 1
    assert workspace_metrics[0].metric_name == AnalyticsMetricType.CUSTOMER_REPLIES
    assert workspace_metrics[0].value == 2
    assert workspace_metrics[0].target_type == "workspace"
    
    # Check customer metrics
    customer_metrics = await query_svc.get_customer_metrics(async_session, workspace_id, customer_id)
    assert len(customer_metrics) == 1
    assert customer_metrics[0].metric_name == AnalyticsMetricType.CUSTOMER_REPLIES
    assert customer_metrics[0].value == 2
    assert customer_metrics[0].target_type == "customer"


@pytest.mark.asyncio
async def test_analytics_projection_meeting_booked(async_session):
    repo = AnalyticsRepository()
    projection = AnalyticsProjection(repo)
    query_svc = AnalyticsQueryService(repo)
    
    workspace_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    meeting_time = datetime.now(timezone.utc).isoformat()
    
    event = MeetingBookedEvent(
        workspace_id=workspace_id,
        customer_id=customer_id,
        actor_type=ActorType.SYSTEM,
        source_subsystem="test",
        meeting_time=meeting_time,
        meeting_url="https://zoom.us/j/123",
        duration_minutes=30
    )
    
    await projection.project_event(event, async_session)
    
    metrics = await query_svc.get_workspace_metrics(async_session, workspace_id)
    assert len(metrics) == 1
    assert metrics[0].metric_name == AnalyticsMetricType.MEETINGS_SCHEDULED
    assert metrics[0].value == 1
