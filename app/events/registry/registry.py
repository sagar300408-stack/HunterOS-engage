from typing import Type, Dict, List, Union, Set
import inspect
from app.events.model.base_event import UniversalBaseEvent
from app.events.bus.interfaces import EventConsumer

class ConsumerRegistry:
    """
    Declarative registry for discovering and routing events to consumers.
    """
    def __init__(self):
        # Maps event_class to a set of registered consumer classes or instances
        self._subscriptions: Dict[Type[UniversalBaseEvent], List[Union[Type[EventConsumer], EventConsumer]]] = {}

    def register(self, event_class: Type[UniversalBaseEvent], consumer: Union[Type[EventConsumer], EventConsumer]):
        """Registers a consumer class or instance for a specific event class."""
        if event_class not in self._subscriptions:
            self._subscriptions[event_class] = []
        if consumer not in self._subscriptions[event_class]:
            self._subscriptions[event_class].append(consumer)

    def get_consumers(self, event_class: Type[UniversalBaseEvent]) -> List[Union[Type[EventConsumer], EventConsumer]]:
        """
        Retrieves all consumers (classes or instances) subscribed to the given event_class
        or its base classes.
        """
        consumers = set()
        
        for cls in inspect.getmro(event_class):
            if issubclass(cls, UniversalBaseEvent):
                if cls in self._subscriptions:
                    consumers.update(self._subscriptions[cls])
                    
        return list(consumers)

# Global registry instance used by decorators
registry = ConsumerRegistry()
