"""
BW5 Certification Test — B22 (Follow-up Decision Logic) + B23 (Follow-up Analytics)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation  # noqa: F401
from app.domain.followup.models import FollowUpQueue, FollowUpExecution
from app.domain.followup.analytics import get_overview
from app.domain.followup.decision_engine import evaluate


# ── B22 Decision Logic Tests ──────────────────────────────────────────────────

class TestB22FollowUpDecisionLogic:
    """
    B22 — Follow-up Decision Logic.
    Tests the decision engine directly — pure synchronous function.
    The decision must be EXPLAINABLE.
    """

    def _base_args(self, **overrides):
        defaults = dict(
            customer_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            last_outgoing_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
            last_incoming_at=datetime.now(tz=timezone.utc) - timedelta(hours=30),
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
        )
        defaults.update(overrides)
        return defaults

    def test_b22_meaningful_signal_triggers_followup(self):
        """Standard inactive lead — should produce follow-up."""
        result = evaluate(**self._base_args())

        assert result.should_follow_up is True
        assert result.reason is not None and len(result.reason) > 0
        assert result.explainability is not None
        assert result.explainability.policy_applied is not None
        assert result.scheduled_for is not None

    def test_b22_max_attempts_reached_no_followup(self):
        """Max attempts exhausted — no follow-up."""
        result = evaluate(**self._base_args(followup_attempt_count=5, max_attempts=5))

        assert result.should_follow_up is False
        assert "Max" in result.reason or "attempt" in result.reason.lower()
        assert result.explainability.confidence == 100

    def test_b22_upcoming_meeting_prevents_followup(self):
        """Active confirmed meeting — should not follow up."""
        next_meeting = datetime.now(tz=timezone.utc) + timedelta(days=1)
        result = evaluate(**self._base_args(
            has_confirmed_meeting=True,
            next_meeting_at=next_meeting,
        ))

        assert result.should_follow_up is False
        assert "meeting" in result.reason.lower() or "Meeting" in result.reason

    def test_b22_high_priority_for_purchase_ready(self):
        """Purchase Ready stage gets shorter delay and high priority."""
        result = evaluate(**self._base_args(
            buying_stage="Purchase Ready",
            last_outgoing_at=datetime.now(tz=timezone.utc) - timedelta(hours=13),
        ))

        assert result.should_follow_up is True
        assert result.priority == "high"

    def test_b22_normal_priority_for_research(self):
        """Research stage gets 48h delay = normal priority."""
        result = evaluate(**self._base_args(
            buying_stage="Research",
            last_outgoing_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
        ))

        assert result.should_follow_up is True
        assert result.priority == "normal"

    def test_b22_idempotency_same_inputs_same_decision(self):
        """Same inputs always produce same decision (no randomness)."""
        args = self._base_args()
        r1 = evaluate(**args)
        r2 = evaluate(**args)
        assert r1.should_follow_up == r2.should_follow_up
        assert r1.reason == r2.reason

    def test_b22_decision_is_explainable(self):
        """Every decision must carry a non-empty explainability report."""
        for stage in ["New Lead", "Research", "Purchase Ready", "Negotiation"]:
            result = evaluate(**self._base_args(buying_stage=stage))
            assert result.explainability is not None, f"No explainability for stage={stage}"
            assert result.explainability.policy_applied
            assert result.explainability.decision_reason
            assert result.explainability.factors_considered is not None


# ── B23 Analytics Tests (Real PostgreSQL DB-backed) ──────────────────────────

@pytest_asyncio.fixture
async def pg_session_followup(pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _create_test_customer(session, workspace_id: uuid.UUID) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        phone=f"+1234{uuid.uuid4().hex[:8]}",
        name="Test Customer B23",
    )
    session.add(customer)
    await session.flush()
    return customer


@pytest.mark.asyncio
async def test_b23_failed_today_derived_from_executions_not_cancelled_queue(pg_session_followup):
    """
    B23 Semantics Verification:
    - Cancelled FollowUpQueue items do NOT increment failed_today.
    - Pending/scheduled items do NOT increment failed_today.
    - Successful FollowUpExecution items do NOT increment failed_today.
    - Only FollowUpExecution items with outcome='failed' occurring today increment failed_today.
    """
    session = pg_session_followup
    workspace_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    customer = await _create_test_customer(session, workspace_id)

    # 1. Cancelled queue item (user cancelled via UI or policy) — NO failed execution
    cancelled_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="cancelled",
        cancellation_reason="Meeting booked by human agent",
        reason="Periodic check-in",
        priority="normal",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(cancelled_fu)

    # 2. Scheduled (pending) queue item
    pending_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="scheduled",
        reason="Follow up on pricing",
        priority="normal",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(pending_fu)

    # 3. Sent queue item with successful execution
    sent_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="sent",
        reason="Follow up on proposal",
        priority="high",
        scheduled_for=now,
        executed_at=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(sent_fu)
    await session.flush()

    exec_success = FollowUpExecution(
        workspace_id=workspace_id,
        followup_id=sent_fu.id,
        attempt_number=1,
        outcome="sent",
        channel="whatsapp",
        message_sent="Hi, following up on our proposal.",
        created_at=now,
    )
    session.add(exec_success)
    await session.flush()

    # Check stats before any failed execution
    stats_before = await get_overview(session, workspace_id)
    assert stats_before.failed_today == 0, (
        f"Expected failed_today=0 (cancelled items must NOT be counted as failed), got {stats_before.failed_today}"
    )
    assert stats_before.sent_today == 1
    assert stats_before.pending_followups == 1

    # 4. Now add a queue item with a FAILED execution (e.g. WhatsApp API rejected)
    failed_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="cancelled",
        cancellation_reason="Provider error: 400 Invalid phone format",
        reason="Urgent reminder",
        priority="urgent",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(failed_fu)
    await session.flush()

    exec_failed = FollowUpExecution(
        workspace_id=workspace_id,
        followup_id=failed_fu.id,
        attempt_number=1,
        outcome="failed",
        channel="whatsapp",
        message_sent="Urgent follow up message",
        failure_reason="Provider error: 400 Invalid phone format",
        created_at=now,
    )
    session.add(exec_failed)
    await session.flush()

    # Check stats after failed execution
    stats_after = await get_overview(session, workspace_id)
    assert stats_after.failed_today == 1, (
        f"Expected failed_today=1 after 1 failed execution, got {stats_after.failed_today}"
    )


@pytest.mark.asyncio
async def test_b23_failed_today_date_boundaries(pg_session_followup):
    """
    B23 Date Boundaries:
    - Failed executions occurring yesterday or earlier must NOT be counted in failed_today.
    - Only failed executions from today_start onwards are counted.
    """
    session = pg_session_followup
    workspace_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today_start - timedelta(hours=5)

    customer = await _create_test_customer(session, workspace_id)

    # Queue item for yesterday's failure
    fu_yesterday = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="cancelled",
        cancellation_reason="Failed yesterday",
        reason="Old check-in",
        priority="normal",
        scheduled_for=yesterday,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(fu_yesterday)
    await session.flush()

    # Yesterday's failed execution
    exec_yesterday = FollowUpExecution(
        workspace_id=workspace_id,
        followup_id=fu_yesterday.id,
        attempt_number=1,
        outcome="failed",
        channel="whatsapp",
        message_sent="Old message",
        failure_reason="Network timeout",
        created_at=yesterday,
    )
    session.add(exec_yesterday)

    # Queue item for today's failure
    fu_today = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="cancelled",
        cancellation_reason="Failed today",
        reason="Today's check-in",
        priority="normal",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(fu_today)
    await session.flush()

    # Today's failed execution
    exec_today = FollowUpExecution(
        workspace_id=workspace_id,
        followup_id=fu_today.id,
        attempt_number=1,
        outcome="failed",
        channel="whatsapp",
        message_sent="Today message",
        failure_reason="Rate limit exceeded",
        created_at=now,
    )
    session.add(exec_today)
    await session.flush()

    stats = await get_overview(session, workspace_id)
    assert stats.failed_today == 1, (
        f"Expected failed_today=1 (only today's execution), got {stats.failed_today}"
    )


@pytest.mark.asyncio
async def test_b23_analytics_multi_tenant_workspace_isolation(pg_session_followup):
    """
    B23 Multi-tenancy / Isolation:
    - Analytics for Workspace A must not count executions or queue items from Workspace B.
    """
    session = pg_session_followup
    workspace_a = uuid.uuid4()
    workspace_b = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    customer_a = await _create_test_customer(session, workspace_a)
    customer_b = await _create_test_customer(session, workspace_b)

    # Workspace A: 2 failed executions today, 1 sent
    for i in range(2):
        fu = FollowUpQueue(
            workspace_id=workspace_a,
            customer_id=customer_a.id,
            status="cancelled",
            cancellation_reason=f"Error {i}",
            reason=f"Reason A {i}",
            priority="normal",
            scheduled_for=now,
            human_paused=False,
            channel="whatsapp",
        )
        session.add(fu)
        await session.flush()
        session.add(FollowUpExecution(
            workspace_id=workspace_a,
            followup_id=fu.id,
            attempt_number=1,
            outcome="failed",
            channel="whatsapp",
            message_sent="Msg A",
            failure_reason="Fail",
            created_at=now,
        ))

    fu_sent_a = FollowUpQueue(
        workspace_id=workspace_a,
        customer_id=customer_a.id,
        status="sent",
        reason="Sent A",
        priority="normal",
        scheduled_for=now,
        executed_at=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(fu_sent_a)

    # Workspace B: 0 failed executions, 1 sent
    fu_sent_b = FollowUpQueue(
        workspace_id=workspace_b,
        customer_id=customer_b.id,
        status="sent",
        reason="Sent B",
        priority="normal",
        scheduled_for=now,
        executed_at=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(fu_sent_b)
    await session.flush()

    stats_a = await get_overview(session, workspace_a)
    stats_b = await get_overview(session, workspace_b)

    assert stats_a.failed_today == 2, f"Workspace A expected failed_today=2, got {stats_a.failed_today}"
    assert stats_a.sent_today == 1, f"Workspace A expected sent_today=1, got {stats_a.sent_today}"

    assert stats_b.failed_today == 0, f"Workspace B expected failed_today=0, got {stats_b.failed_today}"
    assert stats_b.sent_today == 1, f"Workspace B expected sent_today=1, got {stats_b.sent_today}"


@pytest.mark.asyncio
async def test_b23_complete_overview_metrics_accuracy(pg_session_followup):
    """
    B23 Comprehensive Overview Accuracy:
    Verifies pending_followups, due_today, sent_today, failed_today,
    paused_needs_review, and strategy_distribution.
    """
    session = pg_session_followup
    workspace_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    customer = await _create_test_customer(session, workspace_id)

    # 1. Scheduled item due today with strategy 'friendly_reminder'
    session.add(FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="scheduled",
        reason="Check-in 1",
        strategy="friendly_reminder",
        priority="normal",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    ))

    # 2. Scheduled item due today, human_paused=True with strategy 'friendly_reminder'
    session.add(FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="scheduled",
        reason="Check-in 2",
        strategy="friendly_reminder",
        priority="high",
        scheduled_for=now,
        human_paused=True,
        channel="whatsapp",
    ))

    # 3. Executing item due today with strategy 'value_add'
    session.add(FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="executing",
        reason="Case study send",
        strategy="value_add",
        priority="normal",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    ))

    # 4. Sent item executed today with strategy 'breakup'
    sent_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="sent",
        reason="Final notice",
        strategy="breakup",
        priority="low",
        scheduled_for=now,
        executed_at=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(sent_fu)
    await session.flush()

    # 5. Failed execution for a cancelled item
    cancelled_failed_fu = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer.id,
        status="cancelled",
        cancellation_reason="Gateway 502",
        reason="Retry check-in",
        strategy="value_add",
        priority="urgent",
        scheduled_for=now,
        human_paused=False,
        channel="whatsapp",
    )
    session.add(cancelled_failed_fu)
    await session.flush()

    session.add(FollowUpExecution(
        workspace_id=workspace_id,
        followup_id=cancelled_failed_fu.id,
        attempt_number=1,
        outcome="failed",
        channel="whatsapp",
        message_sent="Check in message",
        failure_reason="Gateway 502 Bad Gateway",
        created_at=now,
    ))
    await session.flush()

    stats = await get_overview(session, workspace_id)

    # pending_followups = scheduled (2) + executing (1) = 3
    assert stats.pending_followups == 3, f"Expected pending_followups=3, got {stats.pending_followups}"

    # due_today = scheduled/executing with scheduled_for >= today_start = 3
    assert stats.due_today == 3, f"Expected due_today=3, got {stats.due_today}"

    # sent_today = 1
    assert stats.sent_today == 1, f"Expected sent_today=1, got {stats.sent_today}"

    # failed_today = 1 (from FollowUpExecution outcome='failed')
    assert stats.failed_today == 1, f"Expected failed_today=1, got {stats.failed_today}"

    # paused_needs_review = 1 (item #2 has human_paused=True)
    assert stats.paused_needs_review == 1, f"Expected paused_needs_review=1, got {stats.paused_needs_review}"

    # strategy_distribution = {'friendly_reminder': 2, 'value_add': 2, 'breakup': 1}
    assert stats.strategy_distribution.get("friendly_reminder") == 2, f"Strategy count mismatch: {stats.strategy_distribution}"
    assert stats.strategy_distribution.get("value_add") == 2, f"Strategy count mismatch: {stats.strategy_distribution}"
    assert stats.strategy_distribution.get("breakup") == 1, f"Strategy count mismatch: {stats.strategy_distribution}"
