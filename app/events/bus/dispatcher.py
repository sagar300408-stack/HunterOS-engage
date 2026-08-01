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
from app.events.worker.tasks import dispatch_event
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

        IMPORTANT: The entire query + dispatch + state-update loop must run
        inside an explicit BEGIN/COMMIT block. PostgreSQL only holds
        FOR UPDATE SKIP LOCKED row-locks for the duration of the transaction.
        Without session.begin(), the lock is acquired and immediately released,
        making the result set appear empty on subsequent reads.
        """
        async with get_session() as session:
            async with session.begin():
                # STEP 1 — Query
                logger.info("STEP 1: Querying persisted events")
                stmt = (
                    select(EventRecord)
                    .where(EventRecord.lifecycle_state == EventLifecycleState.PERSISTED.value)
                    .with_for_update(skip_locked=True)
                    .limit(self.batch_size)
                )

                result = await session.execute(stmt)
                records = result.scalars().all()

                logger.info("Retrieved %d persisted events", len(records))

                if not records:
                    # session.begin() rolls back cleanly here — no rows, no locks held.
                    return 0

                logger.info("STEP 2: Retrieved %d events to dispatch", len(records))
                published_count = 0

                for record in records:
                    try:
                        logger.info("STEP 3: Publishing event %s", record.event_id)

                        print(f"\n[DEBUG] dispatch_event: {dispatch_event}")
                        print(f"[DEBUG] dispatch_event.app: {dispatch_event.app}")
                        print(f"[DEBUG] dispatch_event.app.conf.broker_url: {dispatch_event.app.conf.broker_url}")

                        dispatch_event.apply_async(
                            args=[str(record.event_id)],
                            queue="event_dispatch"
                        )
                        logger.info("STEP 4: apply_async succeeded for event %s", record.event_id)

                        # Transition to QUEUED — still inside the same transaction
                        logger.info("STEP 5: Updating lifecycle to QUEUED for event %s", record.event_id)
                        record.lifecycle_state = EventLifecycleState.QUEUED.value
                        published_count += 1

                    except OperationalError:
                        # Broker is down — roll back the entire batch so no row is
                        # left stranded in a partially-updated state. The events
                        # remain PERSISTED and will be picked up on the next poll.
                        logger.exception(
                            "Dispatcher exception: outbox_dispatcher_broker_outage — "
                            "rolling back batch, events remain PERSISTED"
                        )
                        raise  # session.begin() context manager will rollback

                    except Exception:
                        logger.exception(
                            "Dispatcher exception: outbox_dispatcher_unexpected_error — "
                            "rolling back batch"
                        )
                        raise  # session.begin() context manager will rollback

                # STEP 6/7 — session.begin() commits here when the block exits normally
                logger.info("STEP 6: Committing transaction (%d events)", published_count)

        logger.info("STEP 7: Commit successful — %d events transitioned to QUEUED", published_count)

        if published_count > 0:
            logger.info("outbox_batch_dispatched count=%d", published_count)

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
