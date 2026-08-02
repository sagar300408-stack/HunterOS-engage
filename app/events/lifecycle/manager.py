"""
HunterOS Engage — Event Lifecycle Manager

Central authority for all EventRecord state transitions.

Every transition:
  1. Validates the move against VALID_TRANSITIONS (raises InvalidLifecycleTransitionError if illegal).
  2. Writes the appropriate timing column(s) atomically with the state change.
  3. Emits a structured lifecycle log with full context before returning.

No code outside this class may mutate lifecycle_state, queued_at,
processing_started_at, or completed_at on an EventRecord.

Public interface:
    queue()       PERSISTED   → QUEUED          (Outbox Dispatcher)
    processing()  QUEUED      → PROCESSING       (Celery worker pickup)
    complete()    PROCESSING  → COMPLETED        (all consumers succeeded)
    retry()       PROCESSING  → RETRYING         (transient failure, under limit)
    dead_letter() PROCESSING  → DEAD_LETTER      (max retries exceeded)
    requeue()     RETRYING    → QUEUED           (Dispatcher re-pickup after backoff)
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState, can_transition
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InvalidLifecycleTransitionError(Exception):
    """Raised when an invalid state transition is attempted on an EventRecord."""
    pass


class LifecycleManager:
    """
    Centralized service for managing EventRecord lifecycle state transitions.

    Enforces the state machine defined in VALID_TRANSITIONS.
    Populates all timing columns (queued_at, processing_started_at, completed_at)
    and emits a structured log entry on every transition.

    Design invariant: the structured log is the LAST operation before returning,
    so it only fires after every timing column and state mutation has been applied.
    A transition that crashes before reaching the log was never committed — the
    log therefore provides a reliable audit trail of committed transitions only.
    """

    @classmethod
    async def _transition(
        cls,
        session: AsyncSession,
        event_id: UUID,
        to_state: EventLifecycleState,
        error_detail: Optional[str] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> EventRecord:
        """
        Core transition engine shared by all public methods.

        Loads the record via the session identity map (no extra round-trip if
        already loaded), validates the transition, mutates timing columns and
        state atomically, then emits a structured log entry.

        Args:
            session:       Active AsyncSession — caller controls commit.
            event_id:      UUID of the EventRecord to transition.
            to_state:      Target lifecycle state.
            error_detail:  Human-readable failure description (RETRYING/DEAD_LETTER).
            next_retry_at: UTC datetime for next retry attempt (RETRYING only).

        Raises:
            ValueError:                     EventRecord not found.
            InvalidLifecycleTransitionError: Transition is not in VALID_TRANSITIONS.
        """
        record = await session.get(EventRecord, event_id)
        if not record:
            raise ValueError(f"EventRecord {event_id} not found.")

        from_state = EventLifecycleState(record.lifecycle_state)

        if not can_transition(from_state, to_state):
            raise InvalidLifecycleTransitionError(
                f"Invalid transition for event {event_id}: "
                f"{from_state.value} → {to_state.value}"
            )

        # All timing columns use the same instant so the record is internally consistent.
        now = datetime.now(timezone.utc)
        record.lifecycle_state = to_state.value

        # ── Timing columns ─────────────────────────────────────────────────────
        # Each state that begins a new phase of the lifecycle stamps its own
        # column. This gives precise per-phase latency for observability queries.

        if to_state == EventLifecycleState.QUEUED:
            # Stamped on every QUEUED entry including re-queues from RETRYING.
            record.queued_at = now

        elif to_state == EventLifecycleState.PROCESSING:
            # Stamped when the Celery worker picks up the task.
            record.processing_started_at = now

        elif to_state == EventLifecycleState.COMPLETED:
            # Stamped when all consumers have returned successfully.
            record.completed_at = now

        elif to_state == EventLifecycleState.RETRYING:
            # Increment the counter BEFORE the log fires so retry_count
            # in the log already reflects the new (post-increment) value.
            record.retry_count += 1
            record.next_retry_at = next_retry_at
            if error_detail:
                record.error_detail = error_detail

        elif to_state == EventLifecycleState.DEAD_LETTER:
            # Terminal state — reuse completed_at as "finalized_at" so
            # observability queries can use a single column across outcomes.
            record.completed_at = now
            if error_detail:
                record.error_detail = error_detail

        elif to_state == EventLifecycleState.REPLAYED:
            # Manual replay — clear stale error context so the event
            # re-enters the pipeline with a clean slate.
            record.error_detail = None

        # ── Structured lifecycle log ───────────────────────────────────────────
        # Emitted after ALL mutations so the log reflects the final committed
        # state of the record. Fields are always present (None if not applicable)
        # to make log queries predictable and schema-stable.
        logger.info(
            "event_lifecycle_transition",
            event_id=str(event_id),
            event_name=record.event_name,
            workspace_id=str(record.workspace_id),
            from_state=from_state.value,
            to_state=to_state.value,
            retry_count=record.retry_count,
            timestamp=now.isoformat(),
            next_retry_at=next_retry_at.isoformat() if next_retry_at else None,
            error_detail=error_detail,
        )

        return record

    # ── Public transition methods ──────────────────────────────────────────────
    # Each method documents its caller so the full dispatch chain is auditable.

    @classmethod
    async def queue(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """
        PERSISTED → QUEUED.

        Called by the Outbox Dispatcher after successfully publishing the
        Celery task. Stamps queued_at with the current UTC time.
        """
        return await cls._transition(session, event_id, EventLifecycleState.QUEUED)

    @classmethod
    async def processing(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """
        QUEUED → PROCESSING.

        Called by the Celery worker at the start of _dispatch_async().
        Stamps processing_started_at with the current UTC time.
        """
        return await cls._transition(session, event_id, EventLifecycleState.PROCESSING)

    @classmethod
    async def complete(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """
        PROCESSING → COMPLETED.

        Called after all consumers have executed without raising.
        Stamps completed_at with the current UTC time.
        """
        return await cls._transition(session, event_id, EventLifecycleState.COMPLETED)

    @classmethod
    async def retry(
        cls,
        session: AsyncSession,
        event_id: UUID,
        next_retry_at: datetime,
        error_detail: Optional[str] = None,
    ) -> EventRecord:
        """
        PROCESSING → RETRYING.

        Called directly on consumer failure when retry_count < max_retries.
        Increments retry_count, sets next_retry_at (exponential backoff
        computed by the caller), and records the error_detail.

        Replaces the old two-step fail() → retry() pattern from Milestone 0.
        """
        return await cls._transition(
            session,
            event_id,
            EventLifecycleState.RETRYING,
            next_retry_at=next_retry_at,
            error_detail=error_detail,
        )

    @classmethod
    async def dead_letter(
        cls,
        session: AsyncSession,
        event_id: UUID,
        error_detail: Optional[str] = None,
    ) -> EventRecord:
        """
        PROCESSING → DEAD_LETTER.

        Called when retry_count >= max_retries (terminal failure), or by
        stale-recovery maintenance when an event cannot be recovered.
        Stamps completed_at as the "finalized_at" timestamp.
        """
        return await cls._transition(
            session,
            event_id,
            EventLifecycleState.DEAD_LETTER,
            error_detail=error_detail,
        )

    @classmethod
    async def requeue(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """
        RETRYING → QUEUED.

        Called by the Outbox Dispatcher when next_retry_at has elapsed.
        Re-stamps queued_at so per-phase latency metrics remain accurate
        across retry cycles.
        """
        return await cls._transition(session, event_id, EventLifecycleState.QUEUED)

    @classmethod
    async def replay(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """
        DEAD_LETTER | COMPLETED → REPLAYED.

        Called by the Reliability API router when an operator manually
        triggers a replay. Clears error_detail so the event re-enters
        the pipeline with a clean slate.
        """
        return await cls._transition(session, event_id, EventLifecycleState.REPLAYED)
