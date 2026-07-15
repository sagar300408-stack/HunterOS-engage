import logging
from typing import List, Type
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from app.events.store.service import EventStoreService

logger = logging.getLogger(__name__)

class EventStoreConsumer(EventConsumer):
    """
    High-priority infrastructure consumer responsible for persisting every event.
    Executes before application-level consumers.
    """
    
    def __init__(self, service: EventStoreService, session: AsyncSession):
        self._service = service
        self._session = session

    def get_priority(self) -> int:
        """
        Return a high priority (100) so the registry sorts this consumer 
        to execute before any application consumers (priority 0).
        """
        return 100

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        """
        Subscribe to UniversalBaseEvent to catch all events regardless of their specific category or class.
        """
        return [UniversalBaseEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        """
        Persists the event using the store service.
        """
        try:
            await self._service.persist_event(self._session, event)
        except Exception as e:
            logger.error(
                "event_store_persistence_failed",
                extra={
                    "event_id": str(event.event_id),
                    "event_name": getattr(event, "event_name", "unknown"),
                    "error": str(e)
                },
                exc_info=True
            )
            # Depending on infrastructure requirements, we might raise this to halt further dispatch,
            # but currently EventBus traps exceptions to isolate failures. 
            raise e
