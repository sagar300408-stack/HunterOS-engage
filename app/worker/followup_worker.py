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
            
        # Send via channel router
        message = fu.final_message or fu.generated_message
        if not message:
            await _mark_failed(session, fu, "No message content", 0)
            return
            
        send_res = await send_message(fu.channel, customer.phone, message)
        duration = int((time.time() - start_time) * 1000)
        
        # Record execution
        execution = FollowUpExecution(
            workspace_id=fu.workspace_id,
            followup_id=fu.id,
            attempt_number=fu.retry_count,
            outcome="sent" if send_res.success else "failed",
            channel=fu.channel,
            message_sent=message,
            provider_message_id=send_res.provider_message_id,
            failure_reason=send_res.failure_reason,
            duration_ms=duration,
        )
        session.add(execution)
        
        if send_res.success:
            fu.status = transition(fu.status, "sent")
            
            # Publish event
            event = UniversalBaseEvent(
                workspace_id=fu.workspace_id,
                category=EventCategory.FOLLOWUP,
                event_name="followup.executed",
                correlation_id=str(fu.id),
                metadata={
                    "customer_id": str(fu.customer_id),
                    "channel": fu.channel,
                    "provider_message_id": send_res.provider_message_id,
                    "reason": fu.reason,
                    "strategy": fu.strategy or "friendly_reminder"
                },
                actor_type=ActorType.SYSTEM,
                source_subsystem="followup_worker"
            )
            local_bus = EventBus(EventStoreService(EventStoreRepository()))
            await local_bus.publish(session, event)
        else:
            if can_retry(fu.retry_count, fu.max_retries):
                fu.status = transition(fu.status, "executing")
                # Backoff could be applied here
                fu.status = "scheduled"  # Set back to scheduled for retry
                # Add delay for retry
                from datetime import timedelta
                fu.scheduled_for = datetime.now(tz=timezone.utc) + timedelta(minutes=15 * fu.retry_count)
            else:
                fu.status = transition(fu.status, "cancelled")
                fu.cancellation_reason = f"Max retries exceeded. Last error: {send_res.failure_reason}"
                
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
