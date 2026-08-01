from typing import Type
from app.events.model.base_event import UniversalBaseEvent
from app.events.registry.registry import registry

def consume(event_class: Type[UniversalBaseEvent]):
    """
    Decorator to register an EventConsumer for a specific event class.
    
    Example:
    @consume(RawWebhookEvent)
    class RawWebhookConsumer(EventConsumer):
        async def handle_event(self, event):
            ...
    """
    def decorator(cls):
        registry.register(event_class, cls)
        return cls
    return decorator
