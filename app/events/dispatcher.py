"""
HunterOS Engage — In-Process Event Dispatcher

Phase 1: Synchronous, in-process event bus.

Phase 2 upgrade path:
    Replace the `dispatch()` body with a Celery task publish or
    Redis Streams `XADD`. All event definitions, subscriptions,
    and handler signatures remain unchanged — zero refactoring.
"""

from collections import defaultdict
from typing import Callable, Type

from app.events.base import BaseEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EventDispatcher:
    """
    Lightweight synchronous event bus.

    Usage:
        dispatcher.subscribe(MessageReceived, my_handler)
        dispatcher.dispatch(MessageReceived(wa_message_id="...", ...))
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[BaseEvent], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[BaseEvent], handler: Callable) -> None:
        """Register a callable to handle a specific event type."""
        self._handlers[event_type].append(handler)
        logger.debug(
            "event_handler_registered",
            event_type=event_type.__name__,
            handler=handler.__qualname__,
        )

    def dispatch(self, event: BaseEvent) -> None:
        """
        Fire an event to all registered handlers.

        Errors in individual handlers are caught and logged so one
        failing handler does not block the rest of the pipeline.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        logger.debug(
            "event_dispatched",
            event_type=event_type.__name__,
            event_id=str(event.event_id),
            handler_count=len(handlers),
        )

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    "event_handler_error",
                    event_type=event_type.__name__,
                    handler=handler.__qualname__,
                    error=str(exc),
                    exc_info=True,
                )

    def clear(self) -> None:
        """Remove all registered handlers. Useful in tests."""
        self._handlers.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────
# Import and use `dispatcher` throughout the application.
dispatcher = EventDispatcher()
