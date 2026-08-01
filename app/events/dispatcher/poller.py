import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import get_settings
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager

logger = logging.getLogger(__name__)

class OutboxPoller:
    """
    Independent Outbox Dispatcher.
    Polls the EventStore for PERSISTED or RETRYING events and dispatches them to Celery.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], celery_app):
        self.settings = get_settings()
        self.session_factory = session_factory
        self.celery_app = celery_app
        self.poll_interval = self.settings.dispatcher_poll_interval
        self.batch_size = self.settings.dispatcher_batch_size
        self._stop_event = asyncio.Event()

    async def run(self):
        """Starts the polling loop."""
        logger.info(
            f"Starting Outbox Poller [{self.settings.dispatcher_worker_id}] "
            f"(Interval: {self.poll_interval}s, Batch: {self.batch_size})"
        )
        while not self._stop_event.is_set():
            try:
                await self.poll_and_dispatch()
            except Exception as e:
                logger.error(f"Error in Outbox Poller loop: {e}", exc_info=True)
            
            # Use wait() with timeout instead of sleep to allow quick shutdown
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass # Expected timeout, continue polling

    async def stop(self):
        """Signals the poller to stop and waits gracefully."""
        logger.info(f"Stopping Outbox Poller [{self.settings.dispatcher_worker_id}]...")
        self._stop_event.set()

    async def poll_and_dispatch(self):
        """Polls a batch of events and dispatches them to the broker."""
        async with self.session_factory() as session:
            # We use FOR UPDATE SKIP LOCKED to ensure multiple dispatchers can run concurrently
            # without row contention.
            
            now = datetime.now(timezone.utc)
            
            stmt = (
                select(EventRecord.event_id)
                .where(
                    or_(
                        EventRecord.lifecycle_state == EventLifecycleState.PERSISTED.value,
                        and_(
                            EventRecord.lifecycle_state == EventLifecycleState.RETRYING.value,
                            or_(
                                EventRecord.next_retry_at.is_(None),
                                EventRecord.next_retry_at <= now
                            )
                        )
                    )
                )
                .order_by(EventRecord.occurred_at.asc())
                .limit(self.batch_size)
                .with_for_update(skip_locked=True)
            )
            
            result = await session.execute(stmt)
            event_ids = result.scalars().all()
            
            if not event_ids:
                return
            
            logger.debug(f"Poller found {len(event_ids)} events to dispatch.")
            
            for event_id in event_ids:
                try:
                    # 1. Enqueue to Broker
                    # We use send_task to decouple from the actual task module
                    self.celery_app.send_task(
                        "app.events.worker.tasks.dispatch_event",
                        args=[str(event_id)],
                        queue="event_dispatch"
                    )
                    
                    # 2. Transition State
                    await LifecycleManager.queue(session, event_id)
                    
                except Exception as e:
                    logger.error(f"Failed to dispatch event {event_id}: {e}")
                    # If dispatch fails (e.g. Redis is down), we don't commit this row's change to QUEUED
                    # The transaction will rollback at the end of the block or we can just ignore and retry later
                    # Actually, if we raise, the whole batch rolls back.
                    # Instead, we just let it rollback or proceed? 
                    # For safety, we will re-raise so the whole batch rolls back and we try again.
                    raise
            
            # Commit the batch
            await session.commit()
