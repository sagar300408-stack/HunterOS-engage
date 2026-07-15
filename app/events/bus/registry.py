import inspect
from collections import defaultdict
from typing import List, Set, Type

from app.events.bus.exceptions import ConsumerRegistrationError
from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent


class ConsumerRegistry:
    """
    Maintains subscriptions of EventConsumers to Event Classes.
    Resolves which consumers should receive a given event based on class inheritance,
    and returns them ordered by priority (highest first).
    """

    def __init__(self):
        # Maps an event class to a set of consumer instances
        self._subscriptions: defaultdict[Type[UniversalBaseEvent], Set[EventConsumer]] = defaultdict(set)

    def register(self, consumer: EventConsumer) -> None:
        """
        Registers a consumer for all its requested event classes.
        """
        if not isinstance(consumer, EventConsumer):
            raise ConsumerRegistrationError(f"Consumer {consumer} must implement EventConsumer interface.")

        subscriptions = consumer.get_subscriptions()
        if not subscriptions:
            return

        for event_class in subscriptions:
            if not inspect.isclass(event_class) or not issubclass(event_class, UniversalBaseEvent):
                raise ConsumerRegistrationError(f"Subscribed class {event_class} must be a subclass of UniversalBaseEvent.")
            self._subscriptions[event_class].add(consumer)

    def get_subscribers(self, event_class: Type[UniversalBaseEvent]) -> List[EventConsumer]:
        """
        Returns all consumers subscribed to the exact event_class or any of its base classes,
        sorted descending by priority.
        """
        subscribers: Set[EventConsumer] = set()
        
        # Traverse the MRO to find all base classes of this event
        for cls in inspect.getmro(event_class):
            if issubclass(cls, UniversalBaseEvent):
                if cls in self._subscriptions:
                    subscribers.update(self._subscriptions[cls])
                    
        # Sort consumers by priority (highest first)
        return sorted(list(subscribers), key=lambda c: c.get_priority(), reverse=True)
