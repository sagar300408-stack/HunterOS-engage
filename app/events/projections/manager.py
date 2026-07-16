import asyncio
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
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

    def get_subscribed_categories(self) -> List[EventCategory]:
        """
        Dynamically aggregates all subscribed categories from all registered projections.
        """
        categories = set()
        for p in self._projections:
            for cat in p.subscribed_categories:
                categories.add(cat)
        return list(categories)

    def get_priority(self) -> int:
        return 50  # Priority 50: runs after EventStoreConsumer (100)

    async def process_event(self, event: UniversalBaseEvent, session: AsyncSession) -> None:
        """
        Routes the event to all projections that subscribe to this event's category.
        """
        tasks = []
        for projection in self._projections:
            if event.category in projection.subscribed_categories or EventCategory.WILDCARD in projection.subscribed_categories:
                # We can execute projections concurrently or sequentially.
                # Since they receive the same session in this flow, running them sequentially
                # is safer for a single DB transaction to avoid concurrent state mutation issues 
                # on the same connection, although they write to different tables.
                # We will await them sequentially here to avoid asyncpg connection conflicts.
                await projection.project_event(event, session)
