import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import get_settings
from app.events.cluster.coordinator import ClusterCoordinator
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager
from app.events.partitioning.scheduler import EnterprisePartitionScheduler
from app.events.priority.aging import PriorityAgingEngine
from app.events.priority.config import PriorityConfig
from app.events.priority.context import SchedulingContext
from app.events.priority.flow_control import FlowController
from app.events.priority.health import QueueHealthMonitor
from app.events.priority.scheduler import AbstractPriorityScheduler, DefaultPriorityScheduler
from app.events.observability.metrics import event_metrics

logger = logging.getLogger(__name__)


class OutboxPoller:
    """
    Independent Outbox Dispatcher.
    Polls the EventStore for PERSISTED or RETRYING events, applies:
      1. ClusterCoordinator (deterministic consistent hash ring ownership filtering)
      2. EnterprisePartitionScheduler (partition locks & fair allocation)
      3. QueueHealthMonitor (real-time queue health & load state)
      4. PriorityScheduler (interface-driven priority ordering & FIFO preservation)
      5. FlowController (adaptive backpressure & overload protection)
    and dispatches final planned events to Celery.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        celery_app,
        coordinator: Optional[ClusterCoordinator] = None,
        scheduler: Optional[EnterprisePartitionScheduler] = None,
        priority_scheduler: Optional[AbstractPriorityScheduler] = None,
        health_monitor: Optional[QueueHealthMonitor] = None,
        flow_controller: Optional[FlowController] = None,
        priority_config: Optional[PriorityConfig] = None,
    ):
        self.settings = get_settings()
        self.session_factory = session_factory
        self.celery_app = celery_app
        self.coordinator = coordinator
        self.priority_config = priority_config or PriorityConfig.from_env()
        self.scheduler = scheduler or EnterprisePartitionScheduler()
        self.priority_scheduler = priority_scheduler or DefaultPriorityScheduler()
        self.health_monitor = health_monitor or QueueHealthMonitor(self.priority_config)
        self.flow_controller = flow_controller or FlowController(self.priority_config)
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
        """
        Polls candidate EventRecord rows with FOR UPDATE SKIP LOCKED,
        applies Partition -> Priority -> Flow Control pipeline, and dispatches to Celery.
        """
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            
            # 1. Select EventRecord entities directly (zero extra DB query needed)
            stmt = (
                select(EventRecord)
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
                .limit(self.batch_size * 2)  # Pre-fetch candidate window
                .with_for_update(skip_locked=True)
            )
            
            result = await session.execute(stmt)
            candidate_records = list(result.scalars().all())
            
            if not candidate_records:
                return

            # 2. Multi-Dispatcher Cluster Ownership Planning
            if self.coordinator:
                assignment_plan = self.coordinator.plan_local_assignments(candidate_records)
                candidate_records = assignment_plan.assigned_events
                event_metrics.set("dispatcher_assignments", assignment_plan.local_owned_count)
                event_metrics.set("dispatcher_load", int(assignment_plan.local_ownership_ratio * 100))
                if not candidate_records:
                    logger.debug(
                        f"All {assignment_plan.total_candidates} candidate events are owned by peer nodes in cluster."
                    )
                    return
            
            # 3. Pure Execution Planning via Partition Scheduler
            partition_plan = self.scheduler.plan_dispatch(
                candidate_records, batch_size=self.batch_size * 2
            )
            
            # 4. Compute Queue Health Snapshot
            health_snapshot = self.health_monitor.compute_snapshot(candidate_records, now=now)

            # 5. Build Immutable SchedulingContext
            context = SchedulingContext(
                candidate_records=candidate_records,
                partition_plan=partition_plan,
                queue_health=health_snapshot,
                load_state=health_snapshot.system_load_state,
                metrics_snapshot=event_metrics.get_snapshot(),
                active_partitions={r.partition_key for r in candidate_records if r.partition_key},
                retry_backlog_count=sum(1 for r in candidate_records if r.lifecycle_state == "RETRYING"),
                config=self.priority_config,
                current_time=now,
                target_batch_size=self.batch_size,
            )

            # 6. Interface-Driven Priority Scheduler Planning
            priority_plan = self.priority_scheduler.plan(context)

            # 7. Adaptive Backpressure & Flow Control
            flow_plan = self.flow_controller.apply_flow_control(
                plan=priority_plan,
                health=health_snapshot,
                base_batch_size=self.batch_size,
            )

            # 7. Update Partition & Pipeline Telemetry Gauges
            event_metrics.set("active_partitions", partition_plan.active_partition_count)
            event_metrics.set("waiting_partitions", partition_plan.waiting_partition_count)
            event_metrics.set("largest_partition", partition_plan.largest_partition_size)
            event_metrics.increment("scheduler_cycles")
            
            if not flow_plan.dispatches_to_execute:
                logger.debug("No eligible dispatches scheduled in this cycle.")
                return

            logger.debug(
                f"Poller dispatching {len(flow_plan.dispatches_to_execute)} events "
                f"({len(flow_plan.deferred_dispatches)} deferred, load_state={flow_plan.load_state.value}). "
                f"Broker: {self.celery_app.conf.broker_url}"
            )
            
            # 8. Dispatch Scheduled Events to Celery & Transition to QUEUED
            for item in flow_plan.dispatches_to_execute:
                try:
                    logger.debug(
                        f"Dispatching event {item.event_id} (partition={item.partition_key}, "
                        f"prio={item.base_priority.value}, eff={item.effective_weight}, "
                        f"policy={item.ordering_policy.value})..."
                    )
                    
                    # Enqueue to Broker
                    self.celery_app.send_task(
                        "app.events.worker.tasks.dispatch_event",
                        args=[
                            str(item.event_id),
                            item.partition_key,
                            item.ordering_policy.value,
                            item.trace_id,
                            item.lock_timeout_seconds,
                        ],
                        queue="event_dispatch"
                    )
                    
                    # Transition State
                    await LifecycleManager.queue(session, item.event_id)

                    # Priority telemetry counter
                    prio_key = f"priority_{item.base_priority.value.lower()}_dispatched"
                    try:
                        event_metrics.increment(prio_key)
                    except KeyError:
                        pass
                    
                except Exception as e:
                    logger.error(
                        f"Failed to dispatch event {item.event_id}. "
                        f"Broker: {self.celery_app.conf.broker_url} | Error: {e}",
                        exc_info=True
                    )
                    raise
            
            # 9. Commit the batch
            await session.commit()
            logger.debug("Batch committed successfully.")
