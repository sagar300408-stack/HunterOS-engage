"""
Comprehensive unit tests for Follow-Up Execution, Event Subscriptions, and Opt-Out Handling.
Covers DEF-07, DEF-08, DEF-10, and Opt-Out Verification.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.domain.followup.decision_engine import evaluate
from app.domain.followup.schemas import FollowUpDecision
from app.events.followup_subscribers import FollowUpMessageStoredConsumer
from app.events.message_events import MessageReceived, MessageStored


def test_followup_consumer_subscribes_to_message_received_and_stored():
    """Verify DEF-08 fix: consumer must subscribe to MessageReceived."""
    consumer = FollowUpMessageStoredConsumer()
    subs = consumer.get_subscriptions()
    assert MessageReceived in subs, "FollowUpMessageStoredConsumer must subscribe to MessageReceived"
    assert MessageStored in subs, "FollowUpMessageStoredConsumer must retain MessageStored subscription"


def test_decision_engine_aborts_on_opt_out():
    """Verify decision engine aborts follow-up when is_opted_out=True."""
    decision = evaluate(
        customer_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        last_outgoing_at=datetime.now(timezone.utc) - timedelta(hours=30),
        last_incoming_at=datetime.now(timezone.utc) - timedelta(hours=35),
        last_followup_sent_at=None,
        followup_attempt_count=0,
        buying_stage="Research",
        urgency="medium",
        has_open_proposal=False,
        has_confirmed_meeting=False,
        next_meeting_at=None,
        has_missed_meeting=False,
        callback_requested=False,
        approval_pending=False,
        budget_mentioned=False,
        budget_paused=False,
        max_attempts=5,
        is_opted_out=True,
    )
    assert decision.should_follow_up is False
    assert "opted out" in decision.reason.lower()
    assert decision.explainability.policy_applied == "Opt-Out Policy"
    assert decision.explainability.confidence == 100


def test_decision_engine_schedules_when_not_opted_out():
    """Verify standard inactive customer still gets scheduled."""
    decision = evaluate(
        customer_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        last_outgoing_at=datetime.now(timezone.utc) - timedelta(hours=30),
        last_incoming_at=datetime.now(timezone.utc) - timedelta(hours=35),
        last_followup_sent_at=None,
        followup_attempt_count=0,
        buying_stage="Research",
        urgency="medium",
        has_open_proposal=False,
        has_confirmed_meeting=False,
        next_meeting_at=None,
        has_missed_meeting=False,
        callback_requested=False,
        approval_pending=False,
        budget_mentioned=False,
        budget_paused=False,
        max_attempts=5,
        is_opted_out=False,
    )
    assert decision.should_follow_up is True
    assert decision.scheduled_for is not None


@pytest.mark.asyncio
async def test_followup_cancellation_logic_on_abort():
    """Verify DEF-10 fix: existing scheduled follow-ups must be cancelled when should_follow_up is False."""
    from app.domain.followup.service import schedule_followup
    from app.domain.followup.models import FollowUpQueue
    from app.domain.customers.models import Customer, CustomerStatus

    mock_session = AsyncMock()
    customer_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    # Existing scheduled item
    existing_item = FollowUpQueue(
        id=uuid.uuid4(),
        customer_id=customer_id,
        workspace_id=workspace_id,
        status="scheduled"
    )

    mock_customer = Customer(
        id=customer_id,
        workspace_id=workspace_id,
        phone="+1234567890",
        status=CustomerStatus.active
    )

    # Mock DB query results
    # 1. pg_advisory_xact_lock
    # 2. last_in
    # 3. last_out
    # 4. last_fu
    # 5. fu_count
    # 6. latest_intent
    # 7. last_in_msg -> "STOP" (triggering opt-out)
    mock_session.execute.side_effect = [
        AsyncMock(), # lock
        AsyncMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[existing_item])))) # existing scheduled query
    ]
    mock_session.scalar.side_effect = [
        datetime.now(timezone.utc) - timedelta(hours=1), # last_in
        datetime.now(timezone.utc) - timedelta(hours=2), # last_out
        None, # last_fu
        0, # fu_count
        None, # latest_intent
        "STOP", # last_in_msg -> Opt-out!
    ]
    mock_session.get.return_value = mock_customer

    result = await schedule_followup(mock_session, customer_id, workspace_id=workspace_id)

    # 1. No new follow-up should be returned
    assert result is None
    # 2. Existing scheduled follow-up must be transitioned to cancelled
    assert existing_item.status == "cancelled"
    assert "opted out" in existing_item.cancellation_reason.lower()
    # 3. Customer status must be updated to inactive
    assert mock_customer.status == CustomerStatus.inactive
