import logging

from app.events.bus.exceptions import EventValidationError
from app.events.bus.interfaces import EventPublisher
from app.events.bus.registry import ConsumerRegistry
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory

logger = logging.getLogger(__name__)


class EventBus(EventPublisher):
    """
    Lightweight, synchronous, in-process Event Bus for HunterOS Phase 7 Milestone 1.
    Routes events to subscribers via the ConsumerRegistry.
    """

    def __init__(self, registry: ConsumerRegistry):
        self._registry = registry

    def publish(self, event: UniversalBaseEvent) -> None:
        """
        Publishes the event to all consumers subscribed to the event's class or base classes.
        """
        self._validate_event(event)

        event_class = type(event)
        subscribers = self._registry.get_subscribers(event_class)

        logger.info(
            "event_published",
            extra={
                "event_id": str(event.event_id),
                "event_name": getattr(event, "event_name", "unknown"),
                "category": event.category.value if event.category else None,
                "subscriber_count": len(subscribers),
            }
        )

        for consumer in subscribers:
            try:
                consumer.handle_event(event)
            except Exception as exc:
                # Isolate consumer failures: one failing consumer must not block the others
                logger.error(
                    "consumer_error",
                    extra={
                        "event_id": str(event.event_id),
                        "consumer": consumer.__class__.__name__,
                        "error": str(exc)
                    },
                    exc_info=True
                )

    def _validate_event(self, event: UniversalBaseEvent) -> None:
        """
        Ensures the event conforms to architectural constraints.
        Pydantic handles basic structural validation on instantiation, but we add custom checks here.
        """
        if not isinstance(event, UniversalBaseEvent):
            raise EventValidationError("Published event must inherit from UniversalBaseEvent.")

        if getattr(event, "category", None) == EventCategory.AI_DECISION:
            if not event.ai_model_version or not event.ai_reason:
                raise EventValidationError("AI_DECISION events must include ai_model_version and ai_reason for explainability.")
