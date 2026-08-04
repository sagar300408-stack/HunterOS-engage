"""
HunterOS Engage — Transactional Outbox Event Bus
app/events/bus/event_bus.py

Publishes events through the Enterprise Idempotency Engine and transactional outbox.
"""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.exceptions import EventValidationError
from app.events.bus.interfaces import EventPublisher
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.store.models import EventRecord
from app.events.store.service import EventStoreService

logger = logging.getLogger(__name__)


class EventBus(EventPublisher):
    """
    Transactional Outbox Event Bus for HunterOS Engage.
    
    1. Validates event schema.
    2. Evaluates idempotency and persists unique events within the DB transaction.
    3. Gracefully suppresses duplicate deliveries without raising application exceptions.
    4. Enables independent Outbox Dispatcher polling.
    """

    def __init__(self, store_service: EventStoreService):
        self._store_service = store_service

    async def publish(
        self,
        session: AsyncSession,
        event: UniversalBaseEvent,
        is_replay: bool = False,
    ) -> Optional[EventRecord]:
        """
        Validates, evaluates idempotency, and persists the event into the transactional outbox.
        Must be called with an active database session.

        Returns:
            EventRecord (newly persisted or existing duplicate record)
        """
        self._validate_event(event)

        # 1. Evaluate idempotency and persist
        record, decision = await self._store_service.persist_event(
            session=session,
            event=event,
            is_replay=is_replay,
        )

        if decision.is_duplicate:
            logger.info(
                "event_publish_duplicate_suppressed",
                extra={
                    "event_id": str(event.event_id),
                    "existing_event_id": str(record.event_id) if record else None,
                    "event_name": getattr(event, "event_name", "unknown"),
                    "idempotency_key": decision.key,
                    "action": decision.action.value,
                },
            )
            return record

        logger.info(
            "event_persisted_to_outbox",
            extra={
                "event_id": str(event.event_id),
                "event_name": getattr(event, "event_name", "unknown"),
                "category": event.category.value if event.category else None,
                "idempotency_key": decision.key,
            },
        )
        return record

    def _validate_event(self, event: UniversalBaseEvent) -> None:
        """
        Ensures the event conforms to architectural constraints.
        """
        if not isinstance(event, UniversalBaseEvent):
            raise EventValidationError("Published event must inherit from UniversalBaseEvent.")

        if getattr(event, "category", None) == EventCategory.AI_DECISION:
            if not event.ai_model_version or not event.ai_reason:
                raise EventValidationError(
                    "AI_DECISION events must include ai_model_version and ai_reason for explainability."
                )
