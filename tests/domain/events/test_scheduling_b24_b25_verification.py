"""
HunterOS Engage — BW6 Certification Tests
B24: Scheduling State Machine
B25: Conflict Detection

Verification rules:
  - Real PostgreSQL (no mocks for persistence / state transitions)
  - State machine MUST enforce valid transitions and reject invalid ones
  - Every state transition MUST produce an EventAuditLog entry
  - Conflict detector MUST detect real overlaps scoped to workspace_id
  - Cross-workspace events MUST NOT be counted as conflicts (tenant isolation)
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── Import all models in dependency order ─────────────────────────────────────
from app.domain.conversations.models import Base, Conversation, Message  # noqa: F401
from app.domain.customers.models import Customer                          # noqa: F401
from app.domain.intent.models import IntentHistory                        # noqa: F401
from app.domain.security.models import User, AuditLog                    # noqa: F401
from app.domain.memory.models import CustomerMemory, CustomerMemoryEvent  # noqa: F401
from app.domain.followup.models import FollowUpQueue, FollowUpExecution   # noqa: F401
from app.domain.leads.models import LeadQualificationSnapshot             # noqa: F401
from app.domain.escalation.models import HumanEscalation                  # noqa: F401
from app.domain.approval.models import (                                  # noqa: F401
    ApprovalPolicy, ApprovalRequest, ApprovalDecision,
)
from app.domain.journey.sql_models import JourneyStateModel               # noqa: F401
from app.domain.recommendation.models import RecommendationSnapshot       # noqa: F401
from app.domain.friction.models import (                                  # noqa: F401
    FrictionEvent, FrictionScoreSnapshot, SLAPolicy, WorkflowStageLatency,
)
from app.domain.impact.models import (                                    # noqa: F401
    FinancialConfig, BusinessTargets, BaselineMetrics,
    ImpactEvent, EvidenceTrace, ValueAttribution, ExecutiveImpactReport,
)
from app.domain.context.models import (                                   # noqa: F401
    OrganizationNode, ProductService, WorkflowDefinition, BusinessPolicy,
    CustomerContext, TeamMemberContext, KnowledgeDocument,
    BusinessOntology, KnowledgeGraphEdge, ContextConflict,
)
from app.domain.scheduling.models import (                                # noqa: F401
    ScheduledEvent, SchedulingCandidate, EventAuditLog,
    CustomerAvailabilityPreferences,
)

from app.domain.scheduling.state_machine import (
    InvalidTransitionError,
    VALID_TRANSITIONS,
    can_transition,
    get_allowed_transitions,
    transition,
)
from app.domain.scheduling.conflict_detector import check_conflicts
from app.domain.scheduling.models import ScheduledEvent, EventAuditLog
from app.domain.security.models import DEFAULT_WORKSPACE_ID

pytestmark = pytest.mark.asyncio


# ── Ensure tables exist ───────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def ensure_tables(pg_engine):
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ═════════════════════════════════════════════════════════════════════════════
# B24 — Scheduling State Machine
# ═════════════════════════════════════════════════════════════════════════════

class TestB24StateMachine:
    """
    B24 CERTIFICATION: Every valid transition must succeed and produce an
    EventAuditLog entry. Every invalid transition must be rejected.
    """

    async def _create_event(self, session: AsyncSession, status: str = "pending") -> ScheduledEvent:
        """Helper: insert a ScheduledEvent at an arbitrary status directly into the DB."""
        ev = ScheduledEvent(
            workspace_id=DEFAULT_WORKSPACE_ID,
            event_type="meeting",
            title="B24 test event",
            status=status,
        )
        session.add(ev)
        await session.flush()
        return ev

    async def test_b24_pending_to_confirmed(self, pg_session: AsyncSession):
        """pending → confirmed is a legal transition; audit log entry is created."""
        from app.domain.scheduling.service import transition_event
        from app.domain.scheduling.schemas import TransitionEventRequest

        ev = await self._create_event(pg_session, status="pending")
        event_id = ev.id
        await pg_session.commit()

        async with pg_session.begin_nested():
            req = TransitionEventRequest(new_status="confirmed")
            updated = await transition_event(
                session=pg_session,
                event_id=event_id,
                req=req,
                actor_type="system",
            )

        assert updated.status == "confirmed", \
            f"Expected status 'confirmed', got '{updated.status}'"
        assert updated.audit_log, \
            "B24: No audit log entry was created for the transition"
        last = updated.audit_log[-1]
        assert last.from_status == "pending"
        assert last.to_status == "confirmed"

    async def test_b24_confirmed_to_completed_with_timestamp(self, pg_session: AsyncSession):
        """confirmed → completed sets completed_at timestamp."""
        from app.domain.scheduling.service import transition_event
        from app.domain.scheduling.schemas import TransitionEventRequest

        ev = await self._create_event(pg_session, status="confirmed")
        event_id = ev.id
        await pg_session.commit()

        async with pg_session.begin_nested():
            req = TransitionEventRequest(new_status="completed")
            updated = await transition_event(
                session=pg_session,
                event_id=event_id,
                req=req,
                actor_type="user",
            )

        assert updated.status == "completed"
        assert updated.completed_at is not None, \
            "B24: completed_at must be set when transitioning to 'completed'"

    async def test_b24_invalid_transition_rejected(self, pg_session: AsyncSession):
        """
        completed → confirmed is NOT in VALID_TRANSITIONS.
        service.transition_event() must raise InvalidTransitionError.
        """
        from app.domain.scheduling.service import transition_event
        from app.domain.scheduling.schemas import TransitionEventRequest

        ev = await self._create_event(pg_session, status="completed")
        event_id = ev.id
        await pg_session.commit()

        with pytest.raises(InvalidTransitionError):
            async with pg_session.begin_nested():
                req = TransitionEventRequest(new_status="confirmed")
                await transition_event(
                    session=pg_session,
                    event_id=event_id,
                    req=req,
                    actor_type="user",
                )

    async def test_b24_cancelled_is_terminal(self, pg_session: AsyncSession):
        """
        cancelled → anything MUST be rejected (terminal state).
        """
        from app.domain.scheduling.service import transition_event
        from app.domain.scheduling.schemas import TransitionEventRequest

        ev = await self._create_event(pg_session, status="cancelled")
        event_id = ev.id
        await pg_session.commit()

        for target in ("confirmed", "in_progress", "completed"):
            with pytest.raises(InvalidTransitionError, match="cancelled"):
                async with pg_session.begin_nested():
                    req = TransitionEventRequest(new_status=target)
                    await transition_event(
                        session=pg_session,
                        event_id=event_id,
                        req=req,
                        actor_type="system",
                    )

    async def test_b24_full_happy_path_audit_trail(self, pg_session: AsyncSession):
        """
        Full lifecycle: pending → confirmed → in_progress → completed
        Each step must create an audit log entry in sequence.
        """
        from app.domain.scheduling.service import transition_event
        from app.domain.scheduling.schemas import TransitionEventRequest

        ev = await self._create_event(pg_session, status="pending")
        event_id = ev.id
        await pg_session.commit()

        for from_s, to_s in [
            ("pending", "confirmed"),
            ("confirmed", "in_progress"),
            ("in_progress", "completed"),
        ]:
            async with pg_session.begin_nested():
                req = TransitionEventRequest(new_status=to_s)
                ev = await transition_event(
                    session=pg_session,
                    event_id=event_id,
                    req=req,
                    actor_type="system",
                )
            assert ev.status == to_s, f"Expected '{to_s}', got '{ev.status}'"

        # Final state is completed
        assert ev.status == "completed"
        # At least 3 audit entries (created + 3 transitions = 4 minimum,
        # but we only appended 3 transition entries via transition_event)
        assert len(ev.audit_log) >= 3, \
            f"B24: Expected ≥3 audit entries in full lifecycle, got {len(ev.audit_log)}"


# ═════════════════════════════════════════════════════════════════════════════
# B25 — Conflict Detection
# ═════════════════════════════════════════════════════════════════════════════

class TestB25ConflictDetection:
    """
    B25 CERTIFICATION: Conflict detector must correctly identify overlapping
    events for the same assignee, and must NOT flag events in different
    workspaces (tenant isolation).
    """

    def _make_time(self, hour: int) -> datetime:
        """Return a timezone-aware datetime on a fixed test date."""
        return datetime(2027, 1, 15, hour, 0, 0, tzinfo=timezone.utc)

    async def _insert_event(
        self,
        session: AsyncSession,
        assigned_to: uuid.UUID,
        start: datetime,
        duration_min: int = 60,
        workspace_id: uuid.UUID = DEFAULT_WORKSPACE_ID,
        status: str = "confirmed",
    ) -> ScheduledEvent:
        # Create user to satisfy FK constraint if it doesn't exist
        user = await session.get(User, assigned_to)
        if not user:
            user = User(id=assigned_to, workspace_id=workspace_id, email=f"{assigned_to}@example.com", password_hash="xxx", full_name="Test")
            session.add(user)
            await session.flush()
        
        ev = ScheduledEvent(
            workspace_id=workspace_id,
            assigned_to=assigned_to,
            event_type="meeting",
            title="Conflict test event",
            status=status,
            scheduled_for=start,
            duration_minutes=duration_min,
        )
        session.add(ev)
        await session.flush()
        return ev

    async def test_b25_overlap_detected(self, pg_session: AsyncSession):
        """
        Two events for the same user that overlap must be detected as a conflict.

        Event A: 10:00–11:00
        Proposed: 10:30–11:30 → overlaps A → has_conflict = True
        """
        user_id = uuid.uuid4()
        await self._insert_event(
            pg_session,
            assigned_to=user_id,
            start=self._make_time(10),
            duration_min=60,
        )
        await pg_session.commit()

        result = await check_conflicts(
            session=pg_session,
            assigned_to=user_id,
            scheduled_for=self._make_time(10) + timedelta(minutes=30),
            duration_minutes=60,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )

        assert result.has_conflict is True, \
            "B25: Expected conflict for overlapping event, got has_conflict=False"
        assert len(result.conflicting_events) >= 1

    async def test_b25_adjacent_no_conflict(self, pg_session: AsyncSession):
        """
        Two back-to-back events MUST NOT be reported as conflicts.

        Event A: 10:00–11:00
        Proposed: 11:00–12:00 → adjacent, not overlapping → has_conflict = False
        """
        user_id = uuid.uuid4()
        await self._insert_event(
            pg_session,
            assigned_to=user_id,
            start=self._make_time(10),
            duration_min=60,
        )
        await pg_session.commit()

        result = await check_conflicts(
            session=pg_session,
            assigned_to=user_id,
            scheduled_for=self._make_time(11),
            duration_minutes=60,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )

        assert result.has_conflict is False, \
            "B25: Adjacent events MUST NOT be a conflict. has_conflict should be False"

    async def test_b25_cross_workspace_no_conflict(self, pg_session: AsyncSession):
        """
        An event in workspace B for the same user MUST NOT conflict with
        a proposed event in workspace A. Tenant isolation must be enforced.
        """
        user_id = uuid.uuid4()
        workspace_a = uuid.uuid4()
        workspace_b = uuid.uuid4()

        # Existing event in workspace B at 10:00
        await self._insert_event(
            pg_session,
            assigned_to=user_id,
            start=self._make_time(10),
            duration_min=60,
            workspace_id=workspace_b,
        )
        await pg_session.commit()

        # Check conflicts in workspace A at 10:30 (would overlap if cross-workspace)
        result = await check_conflicts(
            session=pg_session,
            assigned_to=user_id,
            scheduled_for=self._make_time(10) + timedelta(minutes=30),
            duration_minutes=60,
            workspace_id=workspace_a,
        )

        assert result.has_conflict is False, \
            "B25: Cross-workspace events MUST NOT be reported as conflicts (tenant isolation violated)"

    async def test_b25_exclude_self_on_reschedule(self, pg_session: AsyncSession):
        """
        When rescheduling an event, the event being rescheduled must be
        excluded from the conflict check so it doesn't conflict with itself.
        """
        user_id = uuid.uuid4()
        existing = await self._insert_event(
            pg_session,
            assigned_to=user_id,
            start=self._make_time(10),
            duration_min=60,
        )
        await pg_session.commit()

        result = await check_conflicts(
            session=pg_session,
            assigned_to=user_id,
            scheduled_for=self._make_time(10),
            duration_minutes=60,
            exclude_event_id=existing.id,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )

        assert result.has_conflict is False, \
            "B25: exclude_event_id must exclude the event from its own conflict check"

    async def test_b25_cancelled_events_not_counted(self, pg_session: AsyncSession):
        """
        Cancelled events MUST NOT be counted as conflicts.
        (They are terminal and no longer occupy the calendar.)
        """
        user_id = uuid.uuid4()
        await self._insert_event(
            pg_session,
            assigned_to=user_id,
            start=self._make_time(10),
            duration_min=60,
            status="cancelled",
        )
        await pg_session.commit()

        result = await check_conflicts(
            session=pg_session,
            assigned_to=user_id,
            scheduled_for=self._make_time(10),
            duration_minutes=60,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )

        assert result.has_conflict is False, \
            "B25: Cancelled events MUST NOT block time on the calendar"
