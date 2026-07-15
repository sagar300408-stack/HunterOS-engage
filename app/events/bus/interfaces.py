from abc import ABC, abstractmethod
from typing import List, Type

from app.events.model.base_event import UniversalBaseEvent


class EventConsumer(ABC):
    """
    Universal interface for all Event Consumers in HunterOS.
    """

    @abstractmethod
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        """
        Returns a list of event classes this consumer is interested in.
        A consumer can subscribe to a specific concrete event (e.g., CustomerRepliedEvent)
        or a base event category (e.g., ConversationEvent).
        """
        pass

    @abstractmethod
    def handle_event(self, event: UniversalBaseEvent) -> None:
        """
        Process the incoming event. Consumers must handle their own internal errors.
        """
        pass


class EventPublisher(ABC):
    """
    Universal interface for publishing events to the Event Bus.
    """

    @abstractmethod
    def publish(self, event: UniversalBaseEvent) -> None:
        """
        Publish an event to all interested consumers.
        This operation must be non-blocking from the publisher's perspective.
        """
        pass
