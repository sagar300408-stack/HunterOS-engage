from typing import Dict, Tuple

from app.domain.timeline.strategies.base import BaseTimelineStrategy
from app.domain.timeline.strategies.implementations import (
    CustomerReplyProjectionStrategy,
    DefaultProjectionStrategy,
    MeetingProjectionStrategy,
)
from app.domain.timeline.strategies.operations import (
    ActionCreatedStrategy, ActionStatusChangedStrategy,
    ApprovalRequestedStrategy, ApprovalRejectedStrategy, ApprovalApprovedStrategy,
    OrchestrationStartedStrategy, OrchestrationFailedStrategy, ActionCompletedStrategy
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
        
        # Operational Events
        self.register(EventCategory.ACTION, "action.created", ActionCreatedStrategy)
        self.register(EventCategory.ACTION, "action.status.changed", ActionStatusChangedStrategy)
        self.register(EventCategory.ACTION, "action.completed", ActionCompletedStrategy)
        
        self.register(EventCategory.APPROVAL, "approval.requested", ApprovalRequestedStrategy)
        self.register(EventCategory.APPROVAL, "approval.rejected", ApprovalRejectedStrategy)
        self.register(EventCategory.APPROVAL, "approval.approved", ApprovalApprovedStrategy)
        
        self.register(EventCategory.ACTION, "action.orchestration.run.started", OrchestrationStartedStrategy)
        self.register(EventCategory.ACTION, "action.orchestration.run.failed", OrchestrationFailedStrategy)

    def register(self, category: EventCategory, event_name: str, strategy: BaseTimelineStrategy):
        self._strategies[(category, event_name)] = strategy

    def get_strategy(self, category: EventCategory, event_name: str) -> BaseTimelineStrategy:
        return self._strategies.get((category, event_name), self._default)


# Global registry instance
timeline_strategy_registry = TimelineStrategyRegistry()
