"""
Follow-up event subscribers.

Bridges the main conversation pipeline to the Follow-up Engine.
When a message arrives or is sent, we evaluate the lead for follow-up
and recalculate their health score.
"""

import asyncio
from uuid import UUID
from datetime import datetime, timezone

from app.events.dispatcher import dispatcher
from app.events.message_events import MessageStored, ReplySent
from app.integrations.postgres.database import get_session
from app.domain.followup.service import schedule_followup
from app.domain.followup.health_engine import upsert_health_score
from app.domain.followup.sales_memory import record_customer_replied
from app.domain.dashboard.models import DEFAULT_WORKSPACE_ID
from app.utils.logger import get_logger
from app.domain.conversations.models import Conversation
from sqlalchemy import select

logger = get_logger(__name__)


async def _handle_message_async(conversation_id: UUID):
    """Async background worker to process follow-up logic after a message."""
    try:
        async with get_session() as session:
            # 1. Get customer ID
            conv = await session.get(Conversation, conversation_id)
            if not conv or not conv.customer_id:
                return
            
            customer_id = conv.customer_id
            
            # 2. Update health score
            await upsert_health_score(session, customer_id, DEFAULT_WORKSPACE_ID)
            
            # 3. Re-evaluate follow-up needs
            await schedule_followup(session, customer_id, conversation_id, DEFAULT_WORKSPACE_ID)
            
            await session.commit()
    except Exception as exc:
        logger.error("followup_subscriber_error", error=str(exc))


def on_message_stored(event: MessageStored):
    """Triggered when a customer message is received and saved."""
    if event.conversation_id:
        asyncio.create_task(_handle_message_async(event.conversation_id))
        
        # Also record customer replied milestone
        async def _record_reply():
            try:
                async with get_session() as session:
                    conv = await session.get(Conversation, event.conversation_id)
                    if conv and conv.customer_id:
                        await record_customer_replied(session, conv.customer_id, DEFAULT_WORKSPACE_ID)
                        
                        # Find any executing follow-ups and mark as replied
                        from app.domain.followup.models import FollowUpQueue
                        from app.domain.followup.state_machine import transition
                        fu = await session.scalar(
                            select(FollowUpQueue)
                            .where(FollowUpQueue.customer_id == conv.customer_id, FollowUpQueue.status == "sent")
                        )
                        if fu:
                            fu.status = transition(fu.status, "replied")
                        
                        await session.commit()
            except Exception as exc:
                logger.error("record_reply_error", error=str(exc))
                
        asyncio.create_task(_record_reply())


def on_reply_sent(event: ReplySent):
    """Triggered when we send a reply (via the main AI pipeline)."""
    # Note: Event doesn't have conversation_id directly, but we can look it up by phone
    async def _handle_reply():
        try:
            async with get_session() as session:
                from app.domain.customers.models import Customer
                cust = await session.scalar(select(Customer).where(Customer.phone == event.to_phone))
                if cust:
                    # Update health score
                    await upsert_health_score(session, cust.id, DEFAULT_WORKSPACE_ID)
                    
                    # We don't necessarily schedule follow-ups on outgoing replies here, 
                    # the followup worker does its own sending. But it's good to recalculate health.
                    await session.commit()
        except Exception as exc:
            logger.error("reply_sent_subscriber_error", error=str(exc))
            
    asyncio.create_task(_handle_reply())


def register_subscribers():
    """Register all follow-up event handlers."""
    dispatcher.subscribe(MessageStored, on_message_stored)
    dispatcher.subscribe(ReplySent, on_reply_sent)
    logger.info("followup_subscribers_registered")
