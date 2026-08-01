import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState, can_transition

logger = logging.getLogger(__name__)


class InvalidLifecycleTransitionError(Exception):
    """Raised when an invalid state transition is attempted on an EventRecord."""
    pass


class LifecycleManager:
    """
    Centralized service for managing EventRecord lifecycle state transitions.

    Enforces the state machine defined in EventLifecycleState.VALID_TRANSITIONS.
    Populates all timing columns (queued_at, processing_started_at, completed_at)
    and emits structured log entries on every transition.

    Public interface:
        queue()       PERSISTED   → QUEUED
        processing()  QUEUED      → PROCESSING
        complete()    PROCESSING  → COMPLETED
        retry()       PROCESSING  → RETRYING
        dead_letter() PROCESSING  → DEAD_LETTER
        requeue()     RETRYING    → QUEUED  (dispatcher re-pickup)
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
        record = await session.get(EventRecord, event_id)
        if not record:
            raise ValueError(f"EventRecord {event_id} not found.")

        from_state = EventLifecycleState(record.lifecycle_state)

        if not can_transition(from_state, to_state):
            raise InvalidLifecycleTransitionError(
                f"Invalid transition for event {event_id}: "
                f"{from_state.value} → {to_state.value}"
            )

        now = datetime.now(timezone.utc)
        record.lifecycle_state = to_state.value

        # ── Populate timing columns ────────────────────────────────────────────
        if to_state == EventLifecycleState.QUEUED:
            record.queued_at = now

        elif to_state == EventLifecycleState.PROCESSING:
            record.processing_started_at = now

        elif to_state == EventLifecycleState.COMPLETED:
            record.completed_at = now

        elif to_state == EventLifecycleState.RETRYING:
            # Increment retry counter and schedule next attempt
            record.retry_count += 1
            record.next_retry_at = next_retry_at
            if error_detail:
                record.error_detail = error_detail

        elif to_state == EventLifecycleState.DEAD_LETTER:
            # Terminal — record the time of death and final error
            record.completed_at = now  # reuse completed_at as "finalized_at"
            if error_detail:
                record.error_detail = error_detail

        # ── Structured log ────────────────────────────────────────────────────
        logger.info(
            "event_lifecycle_transition",
            extra={
                "event_id": str(event_id),
                "event_name": record.event_name,
                "workspace_id": str(record.workspace_id),
                "from_state": from_state.value,
                "to_state": to_state.value,
                "retry_count": record.retry_count,
            },
        )

        return record

    # ── Public transition methods ──────────────────────────────────────────────

    @classmethod
    async def queue(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """PERSISTED → QUEUED. Called by the Outbox Dispatcher."""
        return await cls._transition(session, event_id, EventLifecycleState.QUEUED)

    @classmethod
    async def processing(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """QUEUED → PROCESSING. Called by the Celery worker on task pickup."""
        return await cls._transition(session, event_id, EventLifecycleState.PROCESSING)

    @classmethod
    async def complete(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        """PROCESSING → COMPLETED. Called after all consumers succeed."""
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
        Replaces the old two-step fail() → retry() pattern.
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
        Called when retry_count >= max_retries.
        Also valid from stale-recovery maintenance when event cannot be recovered.
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
        """
        return await cls._transition(session, event_id, EventLifecycleState.QUEUED)

