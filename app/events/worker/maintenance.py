import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager

logger = logging.getLogger(__name__)


async def _recover_stale_events_async(timeout_minutes: int, max_retries: int) -> int:
    """
    Scans for events stuck in PROCESSING past the timeout threshold and
    transitions them to RETRYING (if retries remain) or DEAD_LETTER (terminal).

    Each event is recovered in its own transaction so a failure on one record
    does not prevent other records from being recovered.
    """
    now = datetime.now(timezone.utc)
    timeout_threshold = now - timedelta(minutes=timeout_minutes)
    recovered_count = 0

    # --- Phase 1: identify stale event IDs (read-only query) ------------------
    async with get_session() as session:
        async with session.begin():
            stmt = (
                select(EventRecord.event_id)
                .where(EventRecord.lifecycle_state == EventLifecycleState.PROCESSING.value)
                .where(EventRecord.processing_started_at < timeout_threshold)
            )
            result = await session.execute(stmt)
            stale_ids = result.scalars().all()

    if not stale_ids:
        return 0

    logger.info("stale_event_recovery_scan found=%d stale events", len(stale_ids))

    # --- Phase 2: recover each event in its own transaction -------------------
    for event_id in stale_ids:
        try:
            async with get_session() as session:
                async with session.begin():
                    record = await session.get(EventRecord, event_id)
                    if record is None:
                        continue  # deleted between scan and recovery

                    # Re-check state — another worker may have already recovered it
                    if record.lifecycle_state != EventLifecycleState.PROCESSING.value:
                        logger.debug(
                            "stale_event_already_recovered event_id=%s state=%s",
                            event_id, record.lifecycle_state,
                        )
                        continue

                    error_detail = (
                        f"Stale recovery: stuck in PROCESSING since "
                        f"{record.processing_started_at} (threshold: {timeout_minutes}m)"
                    )
                    logger.warning(
                        "stale_event_recovering event_id=%s retry_count=%d",
                        event_id, record.retry_count,
                    )

                    if record.retry_count < max_retries:
                        # PROCESSING → RETRYING (valid transition)
                        delay_seconds = (2 ** record.retry_count) * 10
                        next_retry = now + timedelta(seconds=delay_seconds)
                        await LifecycleManager.retry(
                            session,
                            event_id,
                            next_retry_at=next_retry,
                            error_detail=error_detail,
                        )
                    else:
                        # PROCESSING → DEAD_LETTER (terminal)
                        await LifecycleManager.dead_letter(
                            session,
                            event_id,
                            error_detail="Max retries exceeded via stale recovery",
                        )

                    recovered_count += 1
                    # session.begin() commits here on clean exit

        except Exception as e:
            logger.error(
                "stale_event_recovery_failed event_id=%s error=%s",
                event_id, e,
                exc_info=True,
            )

    logger.info("stale_event_recovery_complete recovered=%d", recovered_count)
    return recovered_count


from app.celery_app import celery_app


@celery_app.task(name="app.events.worker.maintenance.recover_stale_events")
def recover_stale_events(timeout_minutes: int = 30, max_retries: int = 5):
    """
    Periodic Beat task — recovers zombie events stuck in PROCESSING.

    Lifecycle paths:
      PROCESSING → RETRYING    (retry_count < max_retries, exponential backoff)
      PROCESSING → DEAD_LETTER (retry_count >= max_retries)
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    recovered_count = loop.run_until_complete(
        _recover_stale_events_async(timeout_minutes, max_retries)
    )

    return {"status": "success", "recovered_count": recovered_count}

