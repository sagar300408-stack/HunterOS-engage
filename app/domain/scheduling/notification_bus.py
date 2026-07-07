"""
HunterOS Engage — Notification Bus (Phase 5 Hook)

Architecture-only in Phase 5 — the bus emits log entries only.

Phase 6 will implement real dispatchers:
  WhatsAppNotificationDispatcher
  EmailNotificationDispatcher
  SMSNotificationDispatcher
  CRMNotificationDispatcher

The Scheduling Engine calls bus.emit() after every state change.
Phase 6 replaces the no-op bus with a real one — zero changes to the
scheduling service are required.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from app.utils.logger import get_logger

logger = get_logger(__name__)


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
    Phase 5: No-op notification bus.

    Logs every notification intent but dispatches nothing.
    Phase 6 will subclass or replace this with real implementations.
    """

    async def emit(self, notification: NotificationEvent) -> None:
        """
        Emit a notification event.

        Phase 5: Logs only.
        Phase 6: Dispatches to WhatsApp, email, SMS, CRM based on workspace config.
        """
        logger.info(
            "notification_bus_emit",
            event_type=notification.event_type,
            scheduled_event_id=str(notification.scheduled_event_id),
            workspace_id=str(notification.workspace_id),
            customer_id=str(notification.customer_id) if notification.customer_id else None,
            note="Phase 5: no-op — Phase 6 will dispatch",
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

# Global bus instance — replace with a configured implementation in Phase 6
notification_bus = NotificationBus()
