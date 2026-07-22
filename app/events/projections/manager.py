import asyncio
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from app.integrations.postgres.database import get_session
from app.events.model.categories import EventCategory
from app.events.projections.base import BaseEventProjection


class ProjectionManager(EventConsumer):
    """
    Acts as the single EventBus consumer for all projections.
    Routes events to registered projections based on their subscriptions.
    """

    def __init__(self):
        self._projections: List[BaseEventProjection] = []

    def register_projection(self, projection: BaseEventProjection):
        """Registers a projection with the manager."""
        self._projections.append(projection)

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        """
        Dynamically subscribes to the base event class. We route internally based on category.
        """
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return 50  # Priority 50: runs after EventStoreConsumer (100)

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        """
        Routes the event to all projections that subscribe to this event's category.
        Uses its own database session.
        """
        async with get_session() as session:
            for projection in self._projections:
                if event.category in projection.subscribed_categories or EventCategory.WILDCARD in projection.subscribed_categories:
                    # We await them sequentially here to avoid asyncpg connection conflicts.
                    await projection.project_event(event, session)
            await session.commit()
