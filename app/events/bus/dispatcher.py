"""
HunterOS Engage — Outbox Dispatcher

Pure Transactional Outbox Dispatcher. Runs as an independent long-running
process. On every poll cycle it executes two passes:

  Pass 1 — New events (PERSISTED):
    SELECT … WHERE lifecycle_state = 'PERSISTED' FOR UPDATE SKIP LOCKED
    → apply_async() → LifecycleManager.queue()   (PERSISTED → QUEUED)

  Pass 2 — Retry events (RETRYING, backoff elapsed):
    SELECT … WHERE lifecycle_state = 'RETRYING' AND next_retry_at <= NOW()
               FOR UPDATE SKIP LOCKED
    → apply_async() → LifecycleManager.requeue() (RETRYING → QUEUED)

Both passes use an explicit BEGIN/COMMIT block so PostgreSQL FOR UPDATE SKIP
LOCKED row-locks are held across the full query + dispatch + state-update
sequence. If the broker is unreachable the transaction rolls back and all rows
remain in their original state, ready for the next poll.

All state mutations go through LifecycleManager so timestamps, state machine
validation, and structured logs remain centralised.
"""

import asyncio
import logging
import signal
from datetime import datetime, timezone
from typing import Optional

from kombu.exceptions import OperationalError
from sqlalchemy import select

from app.integrations.postgres.database import get_session
from app.domain.conversations.models import Base
from app.domain.customers.models import Customer
from app.domain.memory.models import CustomerMemory, CustomerMemoryVersion, CustomerMemoryEvent
from app.domain.intent.models import IntentHistory
from app.domain.security.models import User, AuditLog
from app.domain.dashboard.models import PipelineEvent, BackgroundJob
from app.domain.followup.models import FollowUpQueue, FollowUpExecution, LeadHealthScore, SalesMemoryTimeline

from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager
from app.events.worker.tasks import dispatch_event
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OutboxDispatcher:
    """
    Transactional Outbox Dispatcher.

    Polls the event_store table for events that need dispatching:
      • PERSISTED  — new events published by the Event Bus.
      • RETRYING   — events that previously failed and whose backoff has elapsed.

    Both categories are dispatched to the same Celery task queue and
    transitioned to QUEUED via LifecycleManager so every queued_at timestamp
    is always fresh and accurate.

    Lifecycle paths driven by this class:
        PERSISTED → QUEUED        (process_batch)
        RETRYING  → QUEUED        (process_retry_batch, when next_retry_at <= NOW)
    """

    def __init__(self, batch_size: int = 50, poll_interval: float = 1.0):
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self._running = False

    # ── Pass 1: New events ────────────────────────────────────────────────────

    async def process_batch(self) -> int:
        """
        Fetch a batch of PERSISTED events, publish to Celery, and mark QUEUED.

        The entire query + dispatch + state-update sequence runs inside a single
        BEGIN/COMMIT block so FOR UPDATE SKIP LOCKED row-locks are held until
        the transaction commits. A broker outage rolls back all state changes
        and leaves events in PERSISTED for the next poll.

        Returns:
            Number of events successfully queued in this batch.
        """
        async with get_session() as session:
            async with session.begin():
                stmt = (
                    select(EventRecord)
                    .where(EventRecord.lifecycle_state == EventLifecycleState.PERSISTED.value)
                    .with_for_update(skip_locked=True)
                    .limit(self.batch_size)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                if not records:
                    return 0

                logger.info(
                    "outbox_persisted_batch_found",
                    count=len(records),
                )

                published_count = 0

                for record in records:
                    try:
                        logger.info(
                            "outbox_dispatching_event",
                            event_id=str(record.event_id),
                            event_name=record.event_name,
                        )

                        dispatch_event.apply_async(
                            args=[str(record.event_id)],
                            queue="event_dispatch",
                        )

                        # PERSISTED → QUEUED via LifecycleManager:
                        #   • stamps queued_at with current UTC time
                        #   • fires event_lifecycle_transition structured log
                        #   • validates the transition against VALID_TRANSITIONS
                        # session.get() resolves from the identity map — no extra
                        # round-trip since the record was already loaded above.
                        await LifecycleManager.queue(session, record.event_id)
                        published_count += 1

                    except OperationalError:
                        logger.exception(
                            "outbox_broker_outage",
                            event_id=str(record.event_id),
                            note="rolling back — events remain PERSISTED",
                        )
                        raise  # session.begin() rolls back the whole batch

                    except Exception:
                        logger.exception(
                            "outbox_dispatch_error",
                            event_id=str(record.event_id),
                        )
                        raise

                logger.info(
                    "outbox_persisted_batch_committing",
                    published_count=published_count,
                )

        logger.info(
            "outbox_persisted_batch_committed",
            published_count=published_count,
        )

        return published_count

    # ── Pass 2: Retry events ──────────────────────────────────────────────────

    async def process_retry_batch(self) -> int:
        """
        Fetch RETRYING events whose backoff window has elapsed, re-publish to
        Celery, and transition them to QUEUED via LifecycleManager.requeue().

        Query condition:
            lifecycle_state = 'RETRYING'
            AND next_retry_at <= NOW()

        The same FOR UPDATE SKIP LOCKED + single-transaction approach is used
        as in process_batch() to prevent double-dispatch under concurrent
        dispatcher instances.

        Returns:
            Number of retry events successfully requeued in this batch.
        """
        now = datetime.now(timezone.utc)

        async with get_session() as session:
            async with session.begin():
                stmt = (
                    select(EventRecord)
                    .where(EventRecord.lifecycle_state == EventLifecycleState.RETRYING.value)
                    .where(EventRecord.next_retry_at <= now)
                    .with_for_update(skip_locked=True)
                    .limit(self.batch_size)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                if not records:
                    return 0

                logger.info(
                    "outbox_retry_batch_found",
                    count=len(records),
                    evaluated_at=now.isoformat(),
                )

                requeued_count = 0

                for record in records:
                    try:
                        logger.info(
                            "outbox_requeuing_retry_event",
                            event_id=str(record.event_id),
                            event_name=record.event_name,
                            retry_count=record.retry_count,
                            next_retry_at=(
                                record.next_retry_at.isoformat()
                                if record.next_retry_at else None
                            ),
                        )

                        dispatch_event.apply_async(
                            args=[str(record.event_id)],
                            queue="event_dispatch",
                        )

                        # RETRYING → QUEUED via LifecycleManager.requeue():
                        #   • stamps a fresh queued_at for this retry cycle
                        #   • fires event_lifecycle_transition structured log
                        #   • validates RETRYING → QUEUED in VALID_TRANSITIONS
                        # retry_count is NOT reset here — it was incremented when
                        # the event first entered RETRYING and reflects the total
                        # number of attempts made so far.
                        await LifecycleManager.requeue(session, record.event_id)
                        requeued_count += 1

                    except OperationalError:
                        logger.exception(
                            "outbox_retry_broker_outage",
                            event_id=str(record.event_id),
                            note="rolling back — events remain RETRYING",
                        )
                        raise

                    except Exception:
                        logger.exception(
                            "outbox_retry_dispatch_error",
                            event_id=str(record.event_id),
                        )
                        raise

                logger.info(
                    "outbox_retry_batch_committing",
                    requeued_count=requeued_count,
                )

        logger.info(
            "outbox_retry_batch_committed",
            requeued_count=requeued_count,
        )

        return requeued_count

    # ── Poll loop ─────────────────────────────────────────────────────────────

    async def start(self):
        """
        Starts the continuous polling loop.

        Each iteration runs both passes:
          1. process_batch()       — dispatch new PERSISTED events
          2. process_retry_batch() — requeue RETRYING events whose backoff elapsed

        Sleep strategy:
          • If either pass produced a full batch (== batch_size), sleep briefly
            (0.1s) — there is likely more work waiting.
          • Otherwise sleep poll_interval (default 1s).
          • On error, sleep poll_interval to avoid a tight error loop.
        """
        self._running = True
        logger.info(
            "outbox_dispatcher_started",
            poll_interval=self.poll_interval,
            batch_size=self.batch_size,
        )

        while self._running:
            try:
                new_count = await self.process_batch()
                retry_count = await self.process_retry_batch()
                total = new_count + retry_count

                if total >= self.batch_size:
                    # Full batch processed — likely more rows are waiting.
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(
                    "outbox_dispatcher_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(self.poll_interval)

    def stop(self, signum: Optional[int] = None, frame=None):
        """Gracefully halts the polling loop after the current iteration."""
        logger.info("outbox_dispatcher_stopping", signum=signum)
        self._running = False


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    dispatcher = OutboxDispatcher()

    loop = asyncio.get_running_loop()

    # Windows does not support add_signal_handler on the asyncio loop.
    # Fall back to standard signal module.
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
