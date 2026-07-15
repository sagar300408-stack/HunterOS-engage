from typing import Dict, Tuple

from app.domain.timeline.strategies.base import BaseTimelineStrategy
from app.domain.timeline.strategies.implementations import (
    CustomerReplyProjectionStrategy,
    DefaultProjectionStrategy,
    MeetingProjectionStrategy,
)
from app.events.model.categories import EventCategory


class TimelineStrategyRegistry:
    """
    Maps events (by category and name) to their corresponding Timeline Strategy.
    """

    def __init__(self):
        self._strategies: Dict[Tuple[EventCategory, str], BaseTimelineStrategy] = {}
        self._default = DefaultProjectionStrategy()

        self._register_defaults()

    def _register_defaults(self):
        self.register(EventCategory.CONVERSATION, "customer.replied", CustomerReplyProjectionStrategy())
        self.register(EventCategory.SCHEDULING, "MeetingBookedEvent", MeetingProjectionStrategy())

    def register(self, category: EventCategory, event_name: str, strategy: BaseTimelineStrategy):
        self._strategies[(category, event_name)] = strategy

    def get_strategy(self, category: EventCategory, event_name: str) -> BaseTimelineStrategy:
        return self._strategies.get((category, event_name), self._default)


# Global registry instance
timeline_strategy_registry = TimelineStrategyRegistry()
