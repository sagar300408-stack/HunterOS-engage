import asyncio
import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.base_event import UniversalBaseEvent
from app.events.lifecycle.manager import LifecycleManager, InvalidLifecycleTransitionError
from app.events.registry.registry import registry
from app.events.bus.interfaces import ExecutionPolicy

logger = logging.getLogger(__name__)

async def _dispatch_async(event_id: UUID, max_retries: int) -> None:
    async with get_session() as session:
        try:
            # 1. Transition to PROCESSING
            record = await LifecycleManager.processing(session, event_id)
            await session.commit()
        except InvalidLifecycleTransitionError as e:
            logger.warning(f"Skipping dispatch for {event_id}: {e}")
            return
        except ValueError as e:
            logger.error(str(e))
            return
            
        try:
            # 2. Reconstruct Domain Event
            # Find the actual event class in the registry
            event_dict = record.payload
            event_class = UniversalBaseEvent
            
            for known_class in registry._subscriptions.keys():
                if known_class.__name__ == record.event_name:
                    event_class = known_class
                    break
                    
            event = event_class(**event_dict)
            
            # 3. Get consumers
            consumer_types_or_instances = registry.get_consumers(event_class)
            
            ordered_consumers = []
            parallel_consumers = []
            background_consumers = []
            
            for item in consumer_types_or_instances:
                # If it's a class (from @consume), instantiate it. If it's already an instance, use it.
                consumer = item() if isinstance(item, type) else item
                policy = consumer.get_execution_policy()
                if policy in (ExecutionPolicy.ORDERED, ExecutionPolicy.CRITICAL):
                    ordered_consumers.append(consumer)
                elif policy == ExecutionPolicy.PARALLEL:
                    parallel_consumers.append(consumer)
                elif policy == ExecutionPolicy.BACKGROUND:
                    background_consumers.append(consumer)

            # Sort ordered by priority (highest first)
            ordered_consumers.sort(key=lambda c: c.get_priority(), reverse=True)
            
            has_errors = False
            error_messages = []

            # 4. Execute Consumers
            for consumer in ordered_consumers:
                try:
                    await consumer.handle_event(event)
                except Exception as e:
                    has_errors = True
                    error_messages.append(f"{consumer.__class__.__name__}: {str(e)}")
                    if consumer.get_execution_policy() == ExecutionPolicy.CRITICAL:
                        break

            if parallel_consumers and not has_errors:
                results = await asyncio.gather(
                    *[c.handle_event(event) for c in parallel_consumers],
                    return_exceptions=True
                )
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        has_errors = True
                        error_messages.append(f"{parallel_consumers[i].__class__.__name__}: {str(result)}")

            if background_consumers and not has_errors:
                results = await asyncio.gather(
                    *[c.handle_event(event) for c in background_consumers],
                    return_exceptions=True
                )
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        has_errors = True
                        error_messages.append(f"{background_consumers[i].__class__.__name__}: {str(result)}")

            # 5. Lifecycle Transition — direct from PROCESSING, no FAILED intermediate
            if has_errors:
                error_detail = "; ".join(error_messages)
                if record.retry_count < max_retries:
                    # Exponential backoff: 2^retry_count * 10 s (10s, 20s, 40s …)
                    delay_seconds = (2 ** record.retry_count) * 10
                    next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    await LifecycleManager.retry(
                        session, event_id,
                        next_retry_at=next_retry,
                        error_detail=error_detail,
                    )
                else:
                    await LifecycleManager.dead_letter(
                        session, event_id,
                        error_detail=f"Max retries exceeded: {error_detail}",
                    )
                await session.commit()
            else:
                await LifecycleManager.complete(session, event_id)
                await session.commit()

        except Exception as e:
            # Catch-all for unexpected orchestration errors (e.g. DB down mid-flight)
            logger.error(f"Unexpected error orchestrating event {event_id}: {e}", exc_info=True)
            try:
                record = await session.get(EventRecord, event_id)
                if record and record.retry_count < max_retries:
                    delay_seconds = (2 ** record.retry_count) * 10
                    next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    await LifecycleManager.retry(
                        session, event_id,
                        next_retry_at=next_retry,
                        error_detail=str(e),
                    )
                else:
                    await LifecycleManager.dead_letter(
                        session, event_id,
                        error_detail=f"Max retries exceeded: {e}",
                    )
                await session.commit()
            except Exception as inner_e:
                logger.error(
                    f"Failed to persist error state for event {event_id}: {inner_e}",
                    exc_info=True,
                )

from app.celery_app import celery_app

@celery_app.task(
    name="app.events.worker.tasks.dispatch_event",
    queue="event_dispatch",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=150
)
def dispatch_event(event_id_str: str, max_retries: int = 5):
    """
    Celery task that acts as the Generic Consumer Execution Engine.
    We do NOT use Celery's native retry mechanism. The Event Store acts as the
    source of truth for retries via the RETRYING state.
    """
    event_id = UUID(event_id_str)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(_dispatch_async(event_id, max_retries))
