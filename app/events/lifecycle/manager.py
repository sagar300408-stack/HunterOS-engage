import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState, can_transition

logger = logging.getLogger(__name__)

class InvalidLifecycleTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class LifecycleManager:
    """
    Centralized service for managing EventRecord lifecycle state transitions.
    Enforces the state machine and emits metrics/logs.
    """

    @classmethod
    async def _transition(
        cls,
        session: AsyncSession,
        event_id: UUID,
        to_state: EventLifecycleState,
        error_detail: Optional[str] = None,
        next_retry_at: Optional[datetime] = None
    ) -> EventRecord:
        record = await session.get(EventRecord, event_id)
        if not record:
            raise ValueError(f"EventRecord {event_id} not found.")

        from_state = EventLifecycleState(record.lifecycle_state)

        if not can_transition(from_state, to_state):
            raise InvalidLifecycleTransitionError(
                f"Invalid transition for event {event_id} from {from_state.value} to {to_state.value}"
            )

        now = datetime.now(timezone.utc)
        record.lifecycle_state = to_state.value

        # Timestamps and state-specific logic
        if to_state == EventLifecycleState.QUEUED:
            record.queued_at = now
        elif to_state == EventLifecycleState.PROCESSING:
            record.processing_started_at = now
        elif to_state == EventLifecycleState.COMPLETED:
            record.completed_at = now
            # Log metrics here (e.g., latency = record.completed_at - record.occurred_at)
        elif to_state == EventLifecycleState.FAILED:
            record.error_detail = error_detail
        elif to_state == EventLifecycleState.RETRYING:
            record.retry_count += 1
            record.next_retry_at = next_retry_at
            # Maintain previous error detail unless explicitly overwritten
            if error_detail:
                record.error_detail = error_detail
        elif to_state == EventLifecycleState.DEAD_LETTER:
            if error_detail:
                record.error_detail = error_detail

        logger.info(
            f"Event {event_id} ({record.event_name}) transitioned {from_state.value} -> {to_state.value}",
            extra={
                "event_id": str(event_id),
                "event_name": record.event_name,
                "workspace_id": str(record.workspace_id),
                "from_state": from_state.value,
                "to_state": to_state.value,
            }
        )

        return record

    @classmethod
    async def queue(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        return await cls._transition(session, event_id, EventLifecycleState.QUEUED)

    @classmethod
    async def processing(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        return await cls._transition(session, event_id, EventLifecycleState.PROCESSING)

    @classmethod
    async def complete(cls, session: AsyncSession, event_id: UUID) -> EventRecord:
        return await cls._transition(session, event_id, EventLifecycleState.COMPLETED)

    @classmethod
    async def fail(cls, session: AsyncSession, event_id: UUID, error_detail: str) -> EventRecord:
        return await cls._transition(session, event_id, EventLifecycleState.FAILED, error_detail=error_detail)

    @classmethod
    async def retry(
        cls, session: AsyncSession, event_id: UUID, next_retry_at: datetime, error_detail: Optional[str] = None
    ) -> EventRecord:
        return await cls._transition(
            session, event_id, EventLifecycleState.RETRYING, 
            next_retry_at=next_retry_at, error_detail=error_detail
        )

    @classmethod
    async def dead_letter(cls, session: AsyncSession, event_id: UUID, error_detail: Optional[str] = None) -> EventRecord:
        return await cls._transition(session, event_id, EventLifecycleState.DEAD_LETTER, error_detail=error_detail)
