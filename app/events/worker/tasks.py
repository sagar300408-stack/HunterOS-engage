import asyncio
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.base_event import UniversalBaseEvent
from app.events.lifecycle.manager import LifecycleManager, InvalidLifecycleTransitionError
from app.events.registry.registry import registry
from app.events.worker.orchestrator import ConsumerOrchestrator
from app.events.worker.planner import PlanBuilder
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def _dispatch_async(event_id: UUID, max_retries: int) -> None:
    async with get_session() as session:
        try:
            # 1. Transition to PROCESSING
            record = await LifecycleManager.processing(session, event_id)
            await session.commit()
        except InvalidLifecycleTransitionError as e:
            logger.warning(
                "event_dispatch_skipped_invalid_transition",
                event_id=str(event_id),
                reason=str(e),
            )
            return
        except ValueError as e:
            logger.error(
                "event_dispatch_record_not_found",
                event_id=str(event_id),
                reason=str(e),
            )
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
            
            # 3. Get consumers from registry
            consumer_types_or_instances = registry.get_consumers(event_class)

            # Instantiate class-based consumers (@consume decorator registers types)
            consumers = [
                item() if isinstance(item, type) else item
                for item in consumer_types_or_instances
            ]

            # 4. Build execution plan via DAG / topological sort
            plan = PlanBuilder.build(
                event_name=record.event_name,
                consumers=consumers,
            )

            # 5. Execute all consumers stage-by-stage via the orchestration engine.
            #    ConsumerOrchestrator handles bucketing by ExecutionPolicy,
            #    topological stages, failure isolation, per-consumer timing,
            #    and structured logs.
            report = await ConsumerOrchestrator.run_plan(
                event=event,
                plan=plan,
                event_id=event_id,
            )

            # 5. Lifecycle Transition — driven by the execution report.
            if report.has_errors:
                error_detail = report.error_detail()
                if record.retry_count < max_retries:
                    delay_seconds = (2 ** record.retry_count) * 10
                    next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    logger.warning(
                        "event_consumer_failure_retrying",
                        event_id=str(event_id),
                        event_name=record.event_name,
                        retry_count=record.retry_count,
                        delay_seconds=delay_seconds,
                        next_retry_at=next_retry.isoformat(),
                        error_detail=error_detail,
                    )
                    await LifecycleManager.retry(
                        session, event_id,
                        next_retry_at=next_retry,
                        error_detail=error_detail,
                    )
                else:
                    logger.error(
                        "event_consumer_failure_dead_lettered",
                        event_id=str(event_id),
                        event_name=record.event_name,
                        retry_count=record.retry_count,
                        error_detail=error_detail,
                    )
                    await LifecycleManager.dead_letter(
                        session, event_id,
                        error_detail=f"Max retries exceeded: {error_detail}",
                    )
                await session.commit()
            else:
                await LifecycleManager.complete(session, event_id)
                await session.commit()

        except Exception as e:
            # Catch-all for unexpected orchestration errors (e.g. DB unavailable
            # mid-flight, event class not found, malformed payload, etc.).
            logger.error(
                "event_dispatch_orchestration_error",
                event_id=str(event_id),
                error=str(e),
                exc_info=True,
            )
            try:
                record = await session.get(EventRecord, event_id)
                if record and record.retry_count < max_retries:
                    delay_seconds = (2 ** record.retry_count) * 10
                    next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    logger.warning(
                        "event_orchestration_failure_retrying",
                        event_id=str(event_id),
                        retry_count=record.retry_count,
                        delay_seconds=delay_seconds,
                        next_retry_at=next_retry.isoformat(),
                    )
                    await LifecycleManager.retry(
                        session, event_id,
                        next_retry_at=next_retry,
                        error_detail=str(e),
                    )
                else:
                    logger.error(
                        "event_orchestration_failure_dead_lettered",
                        event_id=str(event_id),
                        retry_count=record.retry_count if record else None,
                    )
                    await LifecycleManager.dead_letter(
                        session, event_id,
                        error_detail=f"Max retries exceeded: {e}",
                    )
                await session.commit()
            except Exception as inner_e:
                logger.error(
                    "event_dispatch_state_persist_failed",
                    event_id=str(event_id),
                    error=str(inner_e),
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
