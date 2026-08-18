"""
Follow-up Background Worker.

Continuously polls FollowUpQueue for scheduled items that are due.
Uses row-level locking (SELECT FOR UPDATE SKIP LOCKED) to allow multiple
worker instances safely.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.postgres.database import get_session
from app.domain.followup.models import FollowUpQueue, FollowUpExecution
from app.domain.followup.state_machine import transition, can_retry
from app.domain.followup.channel_router import send_message
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType
from app.events.bus.event_bus import EventBus
from app.events.store.service import EventStoreService
from app.events.store.repository import EventStoreRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 15


async def process_due_followups():
    """Find and execute all due follow-ups."""
    try:
        async with get_session() as session:
            # 1. Find due items, locked for update
            now = datetime.now(tz=timezone.utc)
            
            # Fetch one at a time to minimize lock time
            q = (
                select(FollowUpQueue)
                .where(
                    FollowUpQueue.status == "scheduled",
                    FollowUpQueue.scheduled_for <= now,
                    FollowUpQueue.human_paused == False
                )
                .order_by(FollowUpQueue.priority.desc(), FollowUpQueue.scheduled_for.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            
            result = await session.execute(q)
            fu = result.scalar()
            
            if not fu:
                return False  # Queue is empty

            logger.info("processing_followup", followup_id=str(fu.id), reason=fu.reason)
            
            # 2. Transition to executing
            fu.status = transition(fu.status, "executing")
            await session.commit()
            
            # 3. Execute
            await _execute_followup(fu.id)
            return True
            
    except Exception as exc:
        logger.error("followup_worker_error", error=str(exc))
        return False


async def _execute_followup(followup_id):
    """Execute a single follow-up."""
    async with get_session() as session:
        fu = await session.get(FollowUpQueue, followup_id)
        if not fu or fu.status != "executing":
            return
            
        fu.retry_count += 1
        fu.executed_at = datetime.now(tz=timezone.utc)
        start_time = time.time()
        
        # We need the customer phone
        from app.domain.customers.models import Customer
        customer = await session.get(Customer, fu.customer_id)
        
        if not customer or not customer.phone:
            await _mark_failed(session, fu, "Customer has no phone number", 0)
            return
            
        # Send via event pipeline
        message = fu.final_message or fu.generated_message
        if not message:
            await _mark_failed(session, fu, "No message content", 0)
            return
            
        # 1. Persist outgoing message
        from app.domain.conversations.schemas import SaveMessageDTO, MessageDirectionEnum
        from app.domain.conversations import service as message_service
        from app.utils.clock import SystemClock
        import uuid
        
        # We need a conversation_id. If none exists on FU, we need one.
        conversation_id = fu.conversation_id
        if not conversation_id:
            conversation = await message_service.get_or_create_conversation(session, customer.phone, customer.id)
            conversation_id = conversation.id

        dto = SaveMessageDTO(
            conversation_id=conversation_id,
            direction=MessageDirectionEnum.outgoing,
            content=message,
            wa_message_id=None,
            timestamp=SystemClock.now(),
        )
        outgoing_msg = await message_service.save_message(session, dto)
        
        duration = int((time.time() - start_time) * 1000)
        
        # 2. Record execution as pending/sent to pipeline
        execution = FollowUpExecution(
            workspace_id=fu.workspace_id,
            followup_id=fu.id,
            attempt_number=fu.retry_count,
            outcome="sent", # we assume sent to pipeline is successful dispatch
            channel=fu.channel,
            message_sent=message,
            provider_message_id=None,
            failure_reason=None,
            duration_ms=duration,
        )
        session.add(execution)
        
        # 3. Publish MessageReadyToSendEvent
        from app.events.message_events import MessageReadyToSendEvent
        ready_event = MessageReadyToSendEvent(
            to_phone=customer.phone,
            content=message,
            conversation_id=str(conversation_id),
            workspace_id=fu.workspace_id,
            customer_id=fu.customer_id,
            message_id=outgoing_msg.id,
            actor_type=ActorType.SYSTEM,
            correlation_id=fu.id,
            causation_id=fu.id,
        )
        
        local_bus = EventBus(EventStoreService(EventStoreRepository()))
        await local_bus.publish(session, ready_event)
        
        # Transition fu
        fu.status = transition(fu.status, "sent")
        
        # Also publish followup.executed
        event = UniversalBaseEvent(
            workspace_id=fu.workspace_id,
            category=EventCategory.FOLLOWUP,
            event_name="followup.executed",
            correlation_id=fu.id,
            causation_id=fu.id,
            metadata={
                "customer_id": str(fu.customer_id),
                "channel": fu.channel,
                "reason": fu.reason,
                "strategy": fu.strategy or "friendly_reminder"
            },
            actor_type=ActorType.SYSTEM,
            source_subsystem="followup_worker"
        )
        await local_bus.publish(session, event)
        await session.commit()


async def _mark_failed(session, fu: FollowUpQueue, reason: str, duration: int):
    execution = FollowUpExecution(
        workspace_id=fu.workspace_id,
        followup_id=fu.id,
        attempt_number=fu.retry_count,
        outcome="failed",
        channel=fu.channel,
        message_sent=fu.final_message or fu.generated_message,
        failure_reason=reason,
        duration_ms=duration,
    )
    session.add(execution)
    fu.status = transition(fu.status, "cancelled")
    fu.cancellation_reason = reason
    await session.commit()


async def worker_loop():
    """Main worker loop."""
    logger.info("followup_worker_started")
    while True:
        try:
            processed = await process_due_followups()
            if not processed:
                # Sleep if queue was empty
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            else:
                # Process next item immediately
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("followup_worker_stopped")
            break
        except Exception as exc:
            logger.error("followup_worker_loop_error", error=str(exc))
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
