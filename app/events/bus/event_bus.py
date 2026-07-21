import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.exceptions import EventValidationError
from app.events.bus.interfaces import EventPublisher
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.store.service import EventStoreService

logger = logging.getLogger(__name__)


class EventBus(EventPublisher):
    """
    Transactional Outbox Event Bus for HunterOS Phase 7.
    
    1. Persists the event synchronously within the DB transaction.
    2. Enqueues a Celery task to distribute the event asynchronously.
    """

    def __init__(self, store_service: EventStoreService):
        self._store_service = store_service

    async def publish(self, session: AsyncSession, event: UniversalBaseEvent) -> None:
        """
        Validates, persists, and queues the event.
        Must be called with an active database session.
        """
        self._validate_event(event)

        # 1. Persist (Stage 4 of Architecture)
        await self._store_service.persist_event(session, event)

        logger.info(
            "event_persisted_to_outbox",
            extra={
                "event_id": str(event.event_id),
                "event_name": getattr(event, "event_name", "unknown"),
                "category": event.category.value if event.category else None,
            }
        )
        
        # 2. Queue for distribution (Stage 5 of Architecture)
        from app.events.tasks import dispatch_event
        # Queueing happens immediately. If the DB transaction rolls back, 
        # the Celery task will fail to find the event and can be discarded/ignored.
        # Alternatively, we could enqueue on commit, but Celery tasks usually handle 
        # missing DB records via retries until the transaction commits.
        dispatch_event.apply_async(
            args=[str(event.event_id)],
            queue="event_dispatch"
        )

    def _validate_event(self, event: UniversalBaseEvent) -> None:
        """
        Ensures the event conforms to architectural constraints.
        """
        if not isinstance(event, UniversalBaseEvent):
            raise EventValidationError("Published event must inherit from UniversalBaseEvent.")

        if getattr(event, "category", None) == EventCategory.AI_DECISION:
            if not event.ai_model_version or not event.ai_reason:
                raise EventValidationError("AI_DECISION events must include ai_model_version and ai_reason for explainability.")
