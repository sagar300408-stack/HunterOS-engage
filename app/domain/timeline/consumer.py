from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.timeline.service import TimelineProjectionEngine
from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory


class TimelineConsumer(EventConsumer):
    """
    Subscribes to all relevant business events to project them into the Timeline.
    Runs at standard priority.
    """
    def __init__(self, projection_engine: TimelineProjectionEngine):
        self.projection_engine = projection_engine

    def get_subscribed_categories(self) -> List[EventCategory]:
        # The Timeline listens to almost all business events to map operational history.
        return [
            EventCategory.CONVERSATION,
            EventCategory.SCHEDULING,
            EventCategory.FOLLOWUP,
            EventCategory.LEAD,
            EventCategory.CUSTOMER,
            EventCategory.WORKSPACE
        ]

    def get_priority(self) -> int:
        return 50  # Standard priority, happens after EventStoreConsumer (100)

    async def process_event(self, event: UniversalBaseEvent, session: AsyncSession) -> None:
        """
        Projects the event into a TimelineEntry.
        """
        await self.projection_engine.project_event(event, session)
