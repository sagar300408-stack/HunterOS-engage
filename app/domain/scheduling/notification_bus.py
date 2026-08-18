"""
HunterOS Engage — Notification Bus

The Scheduling Engine calls bus.emit() after every state change.

Subscribers register via notification_bus.subscribe(event_type, handler)
and are called asynchronously on each emit().

Phase 6 will add real dispatchers:
  WhatsAppNotificationDispatcher
  EmailNotificationDispatcher
  SMSNotificationDispatcher
  CRMNotificationDispatcher
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional
from uuid import UUID

from app.utils.logger import get_logger
from app.events.bus.event_bus import EventBus
from app.events.message_events import MessageReadyToSendEvent

logger = get_logger(__name__)

NotificationHandler = Callable[["NotificationEvent"], Awaitable[None]]


# ── Notification event ─────────────────────────────────────────────────────────

@dataclass
class NotificationEvent:
    """
    A notification intent produced by the Scheduling Engine.

    event_type examples:
        event_created | event_confirmed | event_assigned
        event_completed | event_cancelled | event_rescheduled
    """
    event_type:          str
    scheduled_event_id:  UUID
    workspace_id:        UUID
    customer_id:         Optional[UUID] = None
    customer_phone:      Optional[str]  = None
    assigned_to_user_id: Optional[UUID] = None
    payload:             dict           = field(default_factory=dict)


# ── Bus implementation ─────────────────────────────────────────────────────────

class NotificationBus:
    """
    Notification bus with subscriber support.

    Handlers register via subscribe(event_type, handler).
    emit() logs the event and calls all registered handlers for that event_type.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[NotificationHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: NotificationHandler) -> None:
        """
        Register an async handler for a specific event_type.

        Example:
            notification_bus.subscribe("event_completed", my_handler)
        """
        self._subscribers[event_type].append(handler)
        logger.info("notification_bus_subscribed", event_type=event_type, handler=handler.__qualname__)

    async def emit(self, notification: NotificationEvent) -> None:
        """
        Emit a notification event.

        Logs the event and calls every subscriber registered for this event_type.
        Subscriber errors are caught and logged so one failing handler
        cannot block the others.
        """
        logger.info(
            "notification_bus_emit",
            event_type=notification.event_type,
            scheduled_event_id=str(notification.scheduled_event_id),
            workspace_id=str(notification.workspace_id),
            customer_id=str(notification.customer_id) if notification.customer_id else None,
        )

        handlers = self._subscribers.get(notification.event_type, [])
        for handler in handlers:
            try:
                await handler(notification)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "notification_bus_handler_error",
                    event_type=notification.event_type,
                    handler=handler.__qualname__,
                    error=str(exc),
                    exc_info=True,
                )


# ── Singleton ──────────────────────────────────────────────────────────────────

# Global bus instance shared by the scheduling service and all subscribers.
notification_bus = NotificationBus()


# ── O4: Appointment Notifications ──────────────────────────────────────────────

async def dispatch_whatsapp_notification(notification: NotificationEvent) -> None:
    """
    O4: Appointment Notifications
    Intercept scheduling state changes and map them directly to a MessageReadyToSendEvent.
    """
    if not notification.customer_id:
        logger.warning("notification_bus_dispatch_skipped_no_customer", event_id=str(notification.scheduled_event_id))
        return
        
    # Standard format based on the payload (which contains scheduled_for, etc.)
    time_str = notification.payload.get('scheduled_for', 'a scheduled time')
    message_text = f"Your appointment has been {notification.event_type.split('_')[-1]} for {time_str}."
    
    event = MessageReadyToSendEvent(
        workspace_id=notification.workspace_id,
        customer_id=notification.customer_id,
        to_phone=notification.customer_phone or "unknown",
        message_text=message_text,
        correlation_id=UUID(notification.payload.get('correlation_id')) if notification.payload.get('correlation_id') else notification.scheduled_event_id,
        causation_id=notification.scheduled_event_id,
    )
    
    bus = EventBus()
    await bus.publish(event)
    logger.info("notification_bus_whatsapp_dispatched", event_id=str(notification.scheduled_event_id))


# Subscribe the WhatsApp dispatcher to confirmed and rescheduled events
notification_bus.subscribe("event_confirmed", dispatch_whatsapp_notification)
notification_bus.subscribe("event_rescheduled", dispatch_whatsapp_notification)

