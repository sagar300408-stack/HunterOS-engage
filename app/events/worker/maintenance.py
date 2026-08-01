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
    recovered_count = 0
    now = datetime.now(timezone.utc)
    timeout_threshold = now - timedelta(minutes=timeout_minutes)
    
    async with get_session() as session:
        stmt = (
            select(EventRecord)
            .where(EventRecord.lifecycle_state == EventLifecycleState.PROCESSING.value)
            .where(EventRecord.processing_started_at < timeout_threshold)
        )
        
        result = await session.execute(stmt)
        stale_records = result.scalars().all()
        
        for record in stale_records:
            try:
                error_detail = f"Stale recovery: stuck in PROCESSING since {record.processing_started_at}"
                logger.warning(f"Recovering stale event {record.event_id}: {error_detail}")
                
                if record.retry_count < max_retries:
                    # Delay before retry
                    delay_seconds = (2 ** record.retry_count) * 10
                    next_retry = now + timedelta(seconds=delay_seconds)
                    
                    # Manually bypass standard valid transition because PROCESSING -> RETRYING
                    # is valid for Stale Recovery.
                    await LifecycleManager.retry(
                        session, 
                        record.event_id, 
                        next_retry_at=next_retry, 
                        error_detail=error_detail
                    )
                else:
                    await LifecycleManager.dead_letter(
                        session, 
                        record.event_id, 
                        error_detail="Max retries exceeded via Stale Recovery"
                    )
                
                recovered_count += 1
            except Exception as e:
                logger.error(f"Failed to recover stale event {record.event_id}: {e}", exc_info=True)
                
        if recovered_count > 0:
            await session.commit()
            
    return recovered_count

from app.celery_app import celery_app

@celery_app.task(name="app.events.worker.maintenance.recover_stale_events")
def recover_stale_events(timeout_minutes: int = 30, max_retries: int = 5):
    """
    Periodic maintenance task to find 'zombie' events stuck in the PROCESSING state
    and recover them to RETRYING or DEAD_LETTER.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    recovered_count = loop.run_until_complete(_recover_stale_events_async(timeout_minutes, max_retries))
    
    return {"status": "success", "recovered_count": recovered_count}
