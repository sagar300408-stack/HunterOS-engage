import asyncio
import logging
import signal
from typing import Optional
from kombu.exceptions import OperationalError
from sqlalchemy import select
from app.integrations.postgres.database import get_session

# Import all models to ensure SQLAlchemy mappers initialize correctly
from app.domain.conversations.models import Base
from app.domain.customers.models import Customer
from app.domain.memory.models import CustomerMemory, CustomerMemoryVersion, CustomerMemoryEvent
from app.domain.intent.models import IntentHistory
from app.domain.security.models import User, AuditLog
from app.domain.dashboard.models import PipelineEvent, BackgroundJob
from app.domain.followup.models import FollowUpQueue, FollowUpExecution, LeadHealthScore, SalesMemoryTimeline

from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.tasks import dispatch_event
from app.utils.logger import get_logger

logger = get_logger(__name__)

class OutboxDispatcher:
    """
    Pure Transactional Outbox Dispatcher.
    
    Independent long-running process that polls the Event Store for `PERSISTED` events,
    dispatches them to the configured message broker (Celery/Redis), and transitions 
    them to `QUEUED`.
    """
    
    def __init__(self, batch_size: int = 50, poll_interval: float = 1.0):
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self._running = False
        
    async def process_batch(self) -> int:
        """
        Fetches a batch of PERSISTED events using row-level locking,
        publishes them, and marks them QUEUED.
        Returns the number of events processed.
        """
        async with get_session() as session:
            # 1. Fetch batch with FOR UPDATE SKIP LOCKED
            # This ensures multiple dispatcher instances won't process the same events.
            stmt = select(EventRecord).where(
                EventRecord.lifecycle_state == EventLifecycleState.PERSISTED.value
            ).with_for_update(skip_locked=True).limit(self.batch_size)
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            if not records:
                return 0
                
            published_count = 0
            
            for record in records:
                try:
                    # 2. Publish to Broker
                    dispatch_event.apply_async(
                        args=[str(record.event_id)],
                        queue="event_dispatch"
                    )
                    
                    # 3. Transition to QUEUED
                    record.lifecycle_state = EventLifecycleState.QUEUED.value
                    published_count += 1
                    
                except OperationalError as exc:
                    logger.warning(
                        "outbox_dispatcher_broker_outage",
                        error=str(exc),
                        event_id=str(record.event_id)
                    )
                    # Broker is down. Stop processing this batch. 
                    # Rollback the transaction to release locks and leave events in PERSISTED state.
                    await session.rollback()
                    return published_count
                except Exception as exc:
                    logger.error(
                        "outbox_dispatcher_unexpected_error",
                        error=str(exc),
                        event_id=str(record.event_id),
                        exc_info=True
                    )
                    # Unrelated programming/serialization error.
                    # We still rollback the whole batch because this might be an application bug
                    # or memory issue. We don't want to partially commit safely without more robust DLQ handling here.
                    # Wait, if one event is poisoned, we shouldn't block the queue.
                    # But apply_async shouldn't raise serialization errors since we only pass the string UUID!
                    await session.rollback()
                    return published_count

            # 4. Commit successfully published events
            await session.commit()
            
            if published_count > 0:
                logger.info("outbox_batch_dispatched", count=published_count)
                
            return published_count

    async def start(self):
        """Starts the continuous polling loop."""
        self._running = True
        logger.info("outbox_dispatcher_started", interval=self.poll_interval, batch_size=self.batch_size)
        
        while self._running:
            try:
                processed = await self.process_batch()
                
                # If we processed a full batch, there might be more waiting. Don't sleep long.
                if processed == self.batch_size:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(self.poll_interval)
                    
            except Exception as e:
                logger.error("outbox_dispatcher_loop_error", error=str(e), exc_info=True)
                await asyncio.sleep(self.poll_interval) # Backoff on unexpected DB errors
                
    def stop(self, signum: Optional[int] = None, frame=None):
        """Gracefully halts the polling loop."""
        logger.info("outbox_dispatcher_stopping", signum=signum)
        self._running = False


async def main():
    dispatcher = OutboxDispatcher()
    
    # Setup graceful shutdown handlers
    loop = asyncio.get_running_loop()
    
    # Windows does not support add_signal_handler for SIGINT/SIGTERM natively on asyncio loop.
    # We fallback to standard signal handling.
    def handle_stop(sig, frame):
        loop.create_task(shutdown(dispatcher))
        
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)
    
    await dispatcher.start()

async def shutdown(dispatcher: OutboxDispatcher):
    dispatcher.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
