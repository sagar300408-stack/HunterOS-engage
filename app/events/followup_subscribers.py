"""
Follow-up event subscribers.

Two kinds of subscriptions live here:

1. EventConsumer implementations (on the main EventBus)
   - FollowUpMessageStoredConsumer  → MessageStored
   - FollowUpReplySentConsumer      → ReplySent

2. NotificationBus handler
   - on_event_completed             → "event_completed"
     Called by the Scheduling Service after a ScheduledEvent is completed.
     Evaluates the customer and schedules a follow-up if required.
"""

from typing import List, Type
from uuid import UUID

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.message_events import MessageStored, ReplySent

from app.integrations.postgres.database import get_session
from app.domain.followup.service import schedule_followup
from app.domain.followup.health_engine import upsert_health_score
from app.domain.followup.sales_memory import record_customer_replied
from app.domain.security.models import DEFAULT_WORKSPACE_ID
from app.utils.logger import get_logger
from app.domain.conversations.models import Conversation
from app.domain.customers.models import Customer
from app.domain.followup.models import FollowUpQueue
from app.domain.followup.state_machine import transition
from app.domain.scheduling.notification_bus import NotificationEvent, notification_bus
from sqlalchemy import select

logger = get_logger(__name__)


class FollowUpMessageStoredConsumer(EventConsumer):
    """Triggered when a customer message is received and saved."""
    
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageStored]
        
    def get_execution_policy(self) -> ExecutionPolicy:
        # Background task that shouldn't block the main webhook pipeline
        return ExecutionPolicy.BACKGROUND

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, MessageStored):
            return
            
        if not event.conversation_id:
            return

        try:
            async with get_session() as session:
                # 1. Get customer ID
                conv = await session.get(Conversation, event.conversation_id)
                if not conv or not conv.customer_id:
                    return
                
                customer_id = conv.customer_id
                
                # 2. Update health score
                await upsert_health_score(session, customer_id, DEFAULT_WORKSPACE_ID)
                
                # 3. Re-evaluate follow-up needs
                await schedule_followup(session, customer_id, event.conversation_id, DEFAULT_WORKSPACE_ID)
                
                # 4. Record customer replied milestone
                await record_customer_replied(session, customer_id, DEFAULT_WORKSPACE_ID)
                
                # Find any executing follow-ups and mark as replied
                fu = await session.scalar(
                    select(FollowUpQueue)
                    .where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "sent")
                )
                if fu:
                    fu.status = transition(fu.status, "replied")
                
                await session.commit()
        except Exception as exc:
            logger.error("followup_message_stored_consumer_error", error=str(exc), exc_info=True)


class FollowUpReplySentConsumer(EventConsumer):
    """Triggered when we send a reply (via the main AI pipeline)."""
    
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [ReplySent]
        
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.BACKGROUND

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, ReplySent):
            return

        try:
            async with get_session() as session:
                cust = await session.scalar(select(Customer).where(Customer.phone == event.to_phone))
                if cust:
                    # Update health score
                    await upsert_health_score(session, cust.id, DEFAULT_WORKSPACE_ID)
                    
                    # We don't necessarily schedule follow-ups on outgoing replies here, 
                    # the followup worker does its own sending. But it's good to recalculate health.
                    await session.commit()
        except Exception as exc:
            logger.error("followup_reply_sent_consumer_error", error=str(exc), exc_info=True)


def register_subscribers():
    """Register all follow-up event handlers. To be replaced by proper EventBus wiring."""
    # Since we are moving to EventBus, this function will no longer use the old dispatcher.
    # It will just return a list of consumer instances to be registered with the new EventBus.
    return [
        FollowUpMessageStoredConsumer(),
        FollowUpReplySentConsumer()
    ]


# ── NotificationBus ────────────────────────────────────────────────────────────

async def on_event_completed(notification: NotificationEvent) -> None:
    """
    Triggered when the Scheduling Service emits an event_completed notification.
    Re-evaluates the customer to determine if a follow-up should be scheduled.
    """
    if not notification.customer_id:
        return

    try:
        logger.info(f"[TRACE] on_event_completed() executed for customer_id: {notification.customer_id}")
        async with get_session() as session:
            # The event is complete; see if we need a follow-up right away
            logger.info("[TRACE] schedule_followup(customer_id) invoked")
            await schedule_followup(
                session, 
                customer_id=notification.customer_id, 
                workspace_id=notification.workspace_id
            )
            await session.commit()
    except Exception as exc:
        logger.error("followup_on_event_completed_error", error=str(exc), exc_info=True)


def register_notification_bus_subscribers() -> None:
    """Register handlers directly on the Scheduling Engine's NotificationBus."""
    notification_bus.subscribe("event_completed", on_event_completed)

