import asyncio
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.base_event import UniversalBaseEvent
from app.events.lifecycle.manager import LifecycleManager, InvalidLifecycleTransitionError
from app.events.registry.registry import registry
from app.events.schema import schema_registry
from app.events.observability.metrics import event_metrics
from app.events.partitioning.lock_manager import get_lock_manager
from app.events.partitioning.ordering import OrderingPolicy
from app.events.worker.orchestrator import ConsumerOrchestrator
from app.events.worker.planner import PlanBuilder
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _dispatch_async(
    event_id: UUID,
    partition_key: Optional[str] = None,
    ordering_policy: Optional[str] = None,
    trace_id_arg: Optional[str] = None,
    lock_timeout_seconds: float = 60.0,
    max_retries: int = 5,
) -> None:
    event_metrics.increment("dispatcher_cycles")
    lock_manager = get_lock_manager()
    lease_token: Optional[str] = None
    is_ordered = (ordering_policy == OrderingPolicy.ORDERED.value or ordering_policy == "ORDERED")

    # 1. Acquire Partition Lock if partition is ORDERED
    if is_ordered and partition_key:
        lease_token = lock_manager.acquire_lock(partition_key, timeout_seconds=lock_timeout_seconds)
        if lease_token:
            event_metrics.increment("partition_locks_acquired")
        else:
            event_metrics.increment("partition_lock_conflicts")
            logger.warning(
                "event_dispatch_partition_locked_conflict",
                event_id=str(event_id),
                partition_key=partition_key,
            )
            # Partition is currently locked by another worker processing an earlier event.
            # Safe return without transitioning to PROCESSING; will be processed in order.
            return

    try:
        async with get_session() as session:
            try:
                # 2. Transition to PROCESSING
                record = await LifecycleManager.processing(session, event_id)
                event_metrics.increment("active_processing")
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

            trace_id = getattr(record, "trace_id", None) or trace_id_arg or str(record.event_id)
            correlation_id = str(record.correlation_id) if record.correlation_id else None
            workspace_id = str(record.workspace_id)
                
            try:
                # 3. Reconstruct Domain Event
                # Shallow-copy the raw payload so we never mutate the
                # SQLAlchemy-managed JSONB dict (or the DB record).
                event_dict = dict(record.payload)
                event_class = UniversalBaseEvent

                for known_class in registry._subscriptions.keys():
                    event_name_field = known_class.model_fields.get("event_name")
                    if event_name_field and event_name_field.default == record.event_name:
                        event_class = known_class
                        break

                # Schema upgrade (in-memory, audit-safe)
                stored_version = event_dict.get("schema_version", 1)
                if schema_registry.needs_upgrade(record.event_name, stored_version):
                    event_dict = schema_registry.upgrade_payload(
                        event_name=record.event_name,
                        payload=event_dict,
                        stored_version=stored_version,
                    )

                event = event_class(**event_dict)
                
                # 4. Get consumers from registry
                consumer_types_or_instances = registry.get_consumers(event_class)

                # Instantiate class-based consumers (@consume decorator registers types)
                consumers = [
                    item() if isinstance(item, type) else item
                    for item in consumer_types_or_instances
                ]

                # 5. Build execution plan via DAG / topological sort
                plan = PlanBuilder.build(
                    event_name=record.event_name,
                    consumers=consumers,
                )

                # 6. Execute all consumers stage-by-stage via orchestration engine
                report = await ConsumerOrchestrator.run_plan(
                    event=event,
                    plan=plan,
                    event_id=event_id,
                )

                # Record Consumer Spans in metadata_payload
                meta = dict(record.metadata_payload or {})
                meta["consumer_spans"] = [r.to_dict() for r in report.results]
                record.metadata_payload = meta

                # 7. Lifecycle Transition — driven by the execution report.
                if report.has_errors:
                    error_detail = report.error_detail()
                    if record.retry_count < max_retries:
                        delay_seconds = (2 ** record.retry_count) * 10
                        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                        logger.warning(
                            "event_consumer_failure_retrying",
                            event_id=str(event_id),
                            event_name=record.event_name,
                            workspace_id=workspace_id,
                            trace_id=trace_id,
                            correlation_id=correlation_id,
                            retry_count=record.retry_count,
                            delay_seconds=delay_seconds,
                            next_retry_at=next_retry.isoformat(),
                            error_detail=error_detail,
                        )
                        event_metrics.decrement("active_processing")
                        event_metrics.increment("retried")
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
                            workspace_id=workspace_id,
                            trace_id=trace_id,
                            correlation_id=correlation_id,
                            retry_count=record.retry_count,
                            error_detail=error_detail,
                        )
                        event_metrics.decrement("active_processing")
                        event_metrics.increment("dead_lettered")
                        event_metrics.increment("failed")
                        await LifecycleManager.dead_letter(
                            session, event_id,
                            error_detail=f"Max retries exceeded: {error_detail}",
                        )
                    await session.commit()
                else:
                    event_metrics.decrement("active_processing")
                    event_metrics.increment("processed")
                    await LifecycleManager.complete(session, event_id)
                    await session.commit()

            except Exception as e:
                # Catch-all for unexpected orchestration errors
                event_metrics.decrement("active_processing")
                event_metrics.increment("failed")
                logger.error(
                    "event_dispatch_orchestration_error",
                    event_id=str(event_id),
                    workspace_id=workspace_id if "workspace_id" in locals() else None,
                    trace_id=trace_id if "trace_id" in locals() else None,
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
                        event_metrics.increment("retried")
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
                        event_metrics.increment("dead_lettered")
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
    finally:
        # 8. Guaranteed Release of Partition Lock Lease
        if lease_token and partition_key:
            released = lock_manager.release_lock(partition_key, lease_token)
            if released:
                event_metrics.increment("partition_locks_released")


from app.celery_app import celery_app

@celery_app.task(
    name="app.events.worker.tasks.dispatch_event",
    queue="event_dispatch",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=150
)
def dispatch_event(
    event_id_str: str,
    partition_key: Optional[str] = None,
    ordering_policy: Optional[str] = "ORDERED",
    trace_id: Optional[str] = None,
    lock_timeout_seconds: float = 60.0,
    max_retries: int = 5,
    *args,
    **kwargs,
):
    """
    Celery task that acts as the Generic Consumer Execution Engine.
    Acquires partition lease lock for ORDERED partitions and executes consumers.
    """
    event_id = UUID(event_id_str)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(
        _dispatch_async(
            event_id=event_id,
            partition_key=partition_key,
            ordering_policy=ordering_policy,
            trace_id_arg=trace_id,
            lock_timeout_seconds=lock_timeout_seconds,
            max_retries=max_retries,
        )
    )
