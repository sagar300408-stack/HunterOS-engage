"""
Unit tests for WhatsApp Outbound Dispatch & Follow-Up Execution (DEF-18 & DEF-19).
Verifies:
  1. _execute_followup() constructs valid MessageReadyToSendEvent without Pydantic validation errors.
  2. The event reaches WhatsAppSendConsumer with required fields intact.
  3. WhatsAppSendConsumer processes successful mocked provider response without attribute errors.
  4. WhatsApp provider failure raises and records ErrorOccurred (retry/error contract).
  5. Post-send failure after successful send does NOT re-raise to caller (eliminates duplicate send risk).
  6. Message identifiers, correlation, and tenant context remain correct throughout the pipeline.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.domain.followup.models import FollowUpQueue
from app.domain.customers.models import Customer
from app.events.message_events import MessageReadyToSendEvent, ReplySent, ErrorOccurred
from app.events.model.actor_types import ActorType
from app.events.model.categories import EventCategory
from app.domain.integration.consumers.whatsapp_send_consumer import WhatsAppSendConsumer
from app.worker.followup_worker import process_due_followups, _execute_followup


@pytest.mark.asyncio
async def test_followup_worker_constructs_valid_event():
    """Requirement 1 & 6: _execute_followup() constructs a valid MessageReadyToSendEvent."""
    fu_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    mock_fu = FollowUpQueue(
        id=fu_id,
        customer_id=cust_id,
        conversation_id=conv_id,
        workspace_id=ws_id,
        status="executing",
        scheduled_for=datetime.now(timezone.utc),
        human_paused=False,
        priority=1,
        generated_message="Test follow-up message",
        retry_count=0
    )

    mock_cust = Customer(
        id=cust_id,
        workspace_id=ws_id,
        phone="+15551234567",
    )

    published_events = []

    async def mock_publish(session, event):
        published_events.append(event)

    mock_session = AsyncMock()
    mock_session.get.side_effect = lambda model, oid: mock_fu if oid == fu_id else mock_cust
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with (
        patch("app.worker.followup_worker.get_session", return_value=mock_session_ctx),
        patch("app.worker.followup_worker.EventBus.publish", side_effect=mock_publish),
    ):
        await _execute_followup(fu_id)

    # Verify that MessageReadyToSendEvent was published without Pydantic validation errors
    ready_events = [e for e in published_events if isinstance(e, MessageReadyToSendEvent)]
    assert len(ready_events) == 1, "Expected exactly one MessageReadyToSendEvent published"

    event = ready_events[0]
    assert event.to_phone == "+15551234567"
    assert event.content == "Test follow-up message"
    assert event.workspace_id == ws_id
    assert event.customer_id == cust_id
    assert event.correlation_id == fu_id
    assert event.causation_id == fu_id
    assert event.actor_type == ActorType.SYSTEM
    assert "message_id" in event.metadata
    assert mock_fu.status == "sent"


@pytest.mark.asyncio
async def test_whatsapp_consumer_success_without_attribute_error():
    """Requirement 2 & 3: WhatsApp consumer processes MessageReadyToSendEvent without attribute error."""
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    corr_id = uuid.uuid4()

    event = MessageReadyToSendEvent(
        to_phone="+15559876543",
        content="Hello from Originyx HunterOS",
        conversation_id=str(uuid.uuid4()),
        workspace_id=ws_id,
        customer_id=cust_id,
        actor_type=ActorType.SYSTEM,
        correlation_id=corr_id,
        metadata={"message_id": str(uuid.uuid4())}
    )

    mock_provider = AsyncMock()
    mock_provider.send_text_message.return_value = "wamid.HBgLMTU1NTk4NzY1NDM="

    published_events = []

    async def mock_publish(session, ev):
        published_events.append(ev)

    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)

    with (
        patch("app.domain.integration.consumers.whatsapp_send_consumer.get_session") as mock_get_sess,
        patch("app.events.bus.event_bus.EventBus.publish", side_effect=mock_publish)
    ):
        mock_sess = AsyncMock()
        mock_get_sess.return_value.__aenter__.return_value = mock_sess

        # Must not raise AttributeError: 'MessageReadyToSendEvent' object has no attribute 'response_message_id'
        await consumer.handle_event(event)

    mock_provider.send_text_message.assert_called_once_with(
        to="+15559876543",
        body="Hello from Originyx HunterOS"
    )

    # Verify ReplySent was published with proper correlation
    reply_events = [e for e in published_events if isinstance(e, ReplySent)]
    assert len(reply_events) == 1
    reply = reply_events[0]
    assert reply.wa_message_id == "wamid.HBgLMTU1NTk4NzY1NDM="
    assert reply.to_phone == "+15559876543"
    assert reply.correlation_id == corr_id
    assert reply.workspace_id == ws_id


@pytest.mark.asyncio
async def test_whatsapp_consumer_provider_failure_raises_and_records_error():
    """Requirement 4: Provider failure records ErrorOccurred and re-raises for retry."""
    event = MessageReadyToSendEvent(
        to_phone="+15559876543",
        content="Fail test message",
        conversation_id=str(uuid.uuid4()),
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
    )

    mock_provider = AsyncMock()
    mock_provider.send_text_message.side_effect = RuntimeError("Meta API HTTP 500 Network Timeout")

    published_events = []

    async def mock_publish(session, ev):
        published_events.append(ev)

    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)

    with (
        patch("app.domain.integration.consumers.whatsapp_send_consumer.get_session") as mock_get_sess,
        patch("app.events.bus.event_bus.EventBus.publish", side_effect=mock_publish)
    ):
        mock_sess = AsyncMock()
        mock_get_sess.return_value.__aenter__.return_value = mock_sess

        # Provider failure MUST be re-raised so dispatcher/worker can retry
        with pytest.raises(RuntimeError, match="Meta API HTTP 500 Network Timeout"):
            await consumer.handle_event(event)

    error_events = [e for e in published_events if isinstance(e, ErrorOccurred)]
    assert len(error_events) == 1
    err = error_events[0]
    assert err.stage == "whatsapp_send"
    assert "Meta API HTTP 500 Network Timeout" in err.error_message


@pytest.mark.asyncio
async def test_whatsapp_consumer_post_send_failure_prevents_duplicate_send():
    """Requirement 5: If send_text_message succeeds but post-send DB commit fails, do NOT re-raise."""
    event = MessageReadyToSendEvent(
        to_phone="+15559876543",
        content="Idempotency test message",
        conversation_id=str(uuid.uuid4()),
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        correlation_id=uuid.uuid4(),
    )

    mock_provider = AsyncMock()
    mock_provider.send_text_message.return_value = "wamid.SUCCESS_DELIVERED_123"

    consumer = WhatsAppSendConsumer(whatsapp_provider=mock_provider)

    with patch("app.domain.integration.consumers.whatsapp_send_consumer.get_session") as mock_get_sess:
        # Simulate database failure during ReplySent publishing
        mock_sess = AsyncMock()
        mock_sess.commit.side_effect = Exception("Database connection lost during post-send commit")
        mock_get_sess.return_value.__aenter__.return_value = mock_sess

        # Must NOT raise exception to caller, because external message is already delivered!
        # Re-raising would cause Celery/outbox to retry and deliver a duplicate message.
        await consumer.handle_event(event)

    # Provider send was called exactly once
    assert mock_provider.send_text_message.call_count == 1
