"""
Tests for Consumer Retry Semantics & Timeline Schema Verification
==================================================================
Verifies:
1. TimelineEntry schema migration: action_id column exists and accepts UUID or None in PostgreSQL.
2. Dual-layer idempotency:
   - Orchestrator Layer: completed_consumers are skipped on retry, preventing duplicate sends.
   - Consumer Guard Layer: WhatsAppSendConsumer skips sending if ReplySent or wa_message_id exists.
3. Genuinely failed external sends remain retryable.
4. Projection and consumer failures remain fully observable and recoverable.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, delete
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine

import app.integrations.postgres.database as db_module
from app.config import get_settings
from app.domain.conversations.models import Message, MessageDirection, Conversation
from app.domain.integration.consumers.whatsapp_send_consumer import WhatsAppSendConsumer
from app.domain.timeline.models import TimelineEntry, TimelineSeverity
from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.message_events import MessageReadyToSendEvent
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.store.models import EventRecord
from app.events.worker.orchestrator import ConsumerOrchestrator, ConsumerStatus
from app.events.worker.planner import PlanBuilder
from app.integrations.postgres.database import get_session


# ── NullPool Fixture to avoid closed event loop issues in asyncpg ─────────────

@pytest_asyncio.fixture(autouse=True)
async def use_nullpool_engine(monkeypatch):
    """
    Ensure every test uses a fresh NullPool async engine so connections
    are not pooled across different pytest-asyncio event loops.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_session_factory", None)
    yield
    await engine.dispose()


# ── Test 1: PostgreSQL Schema Verification (action_id column) ─────────────────

@pytest.mark.asyncio
async def test_timeline_entry_schema_with_and_without_action_id():
    """Verify that PostgreSQL timeline_entries table accepts action_id (UUID and None)."""
    ws_id = uuid.uuid4()
    ev_id_1 = uuid.uuid4()
    ev_id_2 = uuid.uuid4()
    action_uuid = uuid.uuid4()

    entry_with_action = TimelineEntry(
        timeline_id=uuid.uuid4(),
        event_id=ev_id_1,
        workspace_id=ws_id,
        action_id=action_uuid,
        activity_type="test.action.performed",
        severity=TimelineSeverity.NORMAL,
        actor_type=ActorType.SYSTEM,
        actor_id="test_actor",
        source_subsystem="test",
        occurred_at=datetime.now(timezone.utc),
        structured_data={"test": True},
    )

    entry_without_action = TimelineEntry(
        timeline_id=uuid.uuid4(),
        event_id=ev_id_2,
        workspace_id=ws_id,
        action_id=None,
        activity_type="test.action.performed",
        severity=TimelineSeverity.NORMAL,
        actor_type=ActorType.SYSTEM,
        actor_id="test_actor",
        source_subsystem="test",
        occurred_at=datetime.now(timezone.utc),
        structured_data={"test": False},
    )

    async with get_session() as session:
        session.add(entry_with_action)
        session.add(entry_without_action)
        await session.commit()

        # Query back and verify
        res_1 = await session.execute(
            select(TimelineEntry).where(TimelineEntry.event_id == ev_id_1)
        )
        saved_1 = res_1.scalar_one_or_none()
        assert saved_1 is not None
        assert saved_1.action_id == action_uuid

        res_2 = await session.execute(
            select(TimelineEntry).where(TimelineEntry.event_id == ev_id_2)
        )
        saved_2 = res_2.scalar_one_or_none()
        assert saved_2 is not None
        assert saved_2.action_id is None

        # Clean up test rows
        await session.execute(
            delete(TimelineEntry).where(TimelineEntry.workspace_id == ws_id)
        )
        await session.commit()


# ── Test 2: Orchestrator Layer: Skip Completed Consumers on Retry ─────────────

class FailingOrderedConsumer(EventConsumer):
    def __init__(self, fail_first_time: bool = True):
        self.fail = fail_first_time
        self.call_count = 0

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_priority(self) -> int:
        return 50

    def get_subscriptions(self):
        return [MessageReadyToSendEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.call_count += 1
        if self.fail:
            raise RuntimeError("Simulated projection failure")


@pytest.mark.asyncio
async def test_orchestrator_skips_completed_consumers_on_retry():
    """
    Simulate the exact bug:
    Stage 0 contains FailingOrderedConsumer and WhatsAppSendConsumer.
    Attempt 1: WhatsAppSendConsumer succeeds, FailingOrderedConsumer fails.
               Report has errors -> worker marks completed_consumers=["WhatsAppSendConsumer"].
    Attempt 2 (Retry): ConsumerOrchestrator receives completed_consumers={"WhatsAppSendConsumer"}.
               WhatsAppSendConsumer MUST NOT be executed again.
    """
    event = MessageReadyToSendEvent(
        to_phone="+15551234567",
        content="Test duplicate prevention",
        conversation_id=str(uuid.uuid4()),
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
    )

    mock_provider = AsyncMock()
    mock_provider.send_text_message.return_value = "wamid.TEST_123"

    wa_consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)
    failing_consumer = FailingOrderedConsumer(fail_first_time=True)

    consumers = [wa_consumer, failing_consumer]
    plan = PlanBuilder.build(event_name="MessageReadyToSendEvent", consumers=consumers)
    event_id = uuid.uuid4()

    # Attempt 1: failing_consumer fails, wa_consumer succeeds
    report_attempt_1 = await ConsumerOrchestrator.run_plan(
        event=event,
        plan=plan,
        event_id=event_id,
        completed_consumers=None,
    )

    assert report_attempt_1.has_errors is True
    assert mock_provider.send_text_message.call_count == 1

    # Extract succeeded consumers as tasks.py does
    completed = {
        r.consumer_name for r in report_attempt_1.results
        if r.status == ConsumerStatus.SUCCESS
    }
    assert "WhatsAppSendConsumer" in completed
    assert "FailingOrderedConsumer" not in completed

    # Attempt 2 (Retry): failing_consumer is now fixed, wa_consumer passed in completed_consumers
    failing_consumer.fail = False
    report_attempt_2 = await ConsumerOrchestrator.run_plan(
        event=event,
        plan=plan,
        event_id=event_id,
        completed_consumers=completed,
    )

    # wa_consumer MUST NOT have been called again!
    assert mock_provider.send_text_message.call_count == 1

    # Check report results
    wa_result = next(r for r in report_attempt_2.results if r.consumer_name == "WhatsAppSendConsumer")
    assert wa_result.status == ConsumerStatus.SUCCESS
    assert wa_result.duration_ms == 0

    assert report_attempt_2.has_errors is False


# ── Test 3: Consumer Guard Layer: Pre-send ReplySent Idempotency Check ────────

@pytest.mark.asyncio
async def test_whatsapp_consumer_skips_when_reply_sent_exists_in_event_store():
    """
    If worker restarts or crashes before recording metadata, but ReplySent was already committed,
    WhatsAppSendConsumer detects existing ReplySent by correlation_id and skips sending.
    """
    ws_id = uuid.uuid4()
    corr_id = uuid.uuid4()

    # Seed an existing ReplySent event in PostgreSQL
    event_record = EventRecord(
        event_id=uuid.uuid4(),
        workspace_id=ws_id,
        correlation_id=corr_id,
        actor_type="SYSTEM",
        source_subsystem="test",
        category="CONVERSATION",
        event_name="ReplySent",
        occurred_at=datetime.now(timezone.utc),
        payload={"wa_message_id": "wamid.EXISTING_REPLY", "to_phone": "+15559998888"},
        metadata_payload={},
        lifecycle_state="COMPLETED",
    )

    async with get_session() as session:
        session.add(event_record)
        await session.commit()

    mock_provider = AsyncMock()
    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)

    event = MessageReadyToSendEvent(
        to_phone="+15559998888",
        content="Attempting duplicate send",
        conversation_id=str(uuid.uuid4()),
        workspace_id=ws_id,
        actor_type=ActorType.SYSTEM,
        correlation_id=corr_id,
    )

    # Execute consumer handle_event
    await consumer.handle_event(event)

    # Provider send_text_message MUST NOT be called because ReplySent already exists!
    assert mock_provider.send_text_message.call_count == 0

    # Clean up test row
    async with get_session() as session:
        await session.execute(
            delete(EventRecord).where(EventRecord.event_id == event_record.event_id)
        )
        await session.commit()


# ── Test 4: Consumer Guard Layer: Pre-send Message wa_message_id Check ────────

@pytest.mark.asyncio
async def test_whatsapp_consumer_skips_when_message_has_wa_message_id():
    """
    If the event metadata specifies message_id and that message already has wa_message_id,
    WhatsAppSendConsumer skips sending.
    """
    ws_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    # Seed a Message row with existing wa_message_id
    conv = Conversation(
        id=conv_id,
        customer_phone="+15559998888",
        workspace_id=ws_id,
        created_at=datetime.now(timezone.utc),
    )
    msg = Message(
        id=msg_id,
        conversation_id=conv_id,
        direction=MessageDirection.outgoing,
        content="Previously sent message",
        wa_message_id="wamid.PREVIOUSLY_SENT",
        timestamp=datetime.now(timezone.utc),
    )

    async with get_session() as session:
        session.add(conv)
        session.add(msg)
        await session.commit()

    mock_provider = AsyncMock()
    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)

    event = MessageReadyToSendEvent(
        to_phone="+15559998888",
        content="Previously sent message",
        conversation_id=str(conv_id),
        workspace_id=ws_id,
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
        metadata={"message_id": str(msg_id)},
    )

    await consumer.handle_event(event)

    assert mock_provider.send_text_message.call_count == 0

    # Clean up test rows
    async with get_session() as session:
        await session.execute(delete(Message).where(Message.id == msg_id))
        await session.execute(delete(Conversation).where(Conversation.id == conv_id))
        await session.commit()


# ── Test 5: Truly Failed External Send Remains Retryable ──────────────────────

@pytest.mark.asyncio
async def test_genuinely_failed_whatsapp_send_remains_retryable():
    """
    When Meta API fails (e.g. 503), WhatsAppSendConsumer raises,
    is NOT marked completed, and executes again on retry.
    """
    event = MessageReadyToSendEvent(
        to_phone="+15551234567",
        content="Retryable message",
        conversation_id=str(uuid.uuid4()),
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
    )

    mock_provider = AsyncMock()
    # Fails first attempt, succeeds second attempt
    mock_provider.send_text_message.side_effect = [
        RuntimeError("Meta 503 Service Unavailable"),
        "wamid.RETRY_SUCCESS",
    ]

    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)
    plan = PlanBuilder.build(event_name="MessageReadyToSendEvent", consumers=[consumer])

    # Attempt 1: Provider raises error
    report_1 = await ConsumerOrchestrator.run_plan(
        event=event,
        plan=plan,
        event_id=uuid.uuid4(),
        completed_consumers=set(),
    )

    assert report_1.has_errors is True
    wa_result_1 = report_1.results[0]
    assert wa_result_1.failed is True
    assert "Meta 503" in wa_result_1.exception_msg

    # Attempt 2: retry without completed_consumers (since it failed)
    report_2 = await ConsumerOrchestrator.run_plan(
        event=event,
        plan=plan,
        event_id=uuid.uuid4(),
        completed_consumers=set(),
    )

    assert report_2.has_errors is False
    assert mock_provider.send_text_message.call_count == 2
    assert report_2.results[0].status == ConsumerStatus.SUCCESS


# ── Test 6: Observability: Failed Consumers Are Visible & Tracked ─────────────

@pytest.mark.asyncio
async def test_failed_consumer_observability_not_swallowed():
    """
    Verify that consumer failures are never silently swallowed:
    - has_errors is True
    - error_detail contains exact error
    - failure is captured with full diagnostic information
    """
    event = MessageReadyToSendEvent(
        to_phone="+15551234567",
        content="Observability test",
        conversation_id=str(uuid.uuid4()),
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
    )

    failing_consumer = FailingOrderedConsumer(fail_first_time=True)
    plan = PlanBuilder.build(event_name="MessageReadyToSendEvent", consumers=[failing_consumer])

    report = await ConsumerOrchestrator.run_plan(
        event=event,
        plan=plan,
        event_id=uuid.uuid4(),
    )

    assert report.has_errors is True
    assert len(report.error_messages) == 1
    assert "FailingOrderedConsumer" in report.error_detail()
    assert "Simulated projection failure" in report.error_detail()

    failed_result = report.results[0]
    assert failed_result.exception_type == "RuntimeError"
    assert failed_result.traceback is not None
