"""
HunterOS Engage — Runtime Snapshot Generator
app/events/diagnostics/runtime.py

Coordinates concurrent subsystem diagnostics collection under a single
logical observation point to generate consistent, unified RuntimeSnapshots.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.consumers import AbstractConsumerDiagnosticsCollector
from app.events.diagnostics.dispatchers import AbstractDispatcherDiagnosticsCollector
from app.events.diagnostics.health import AbstractRuntimeHealthMonitor
from app.events.diagnostics.locks import AbstractLockDiagnosticsCollector
from app.events.diagnostics.models import RuntimeSnapshot
from app.events.diagnostics.partitions import AbstractPartitionDiagnosticsCollector
from app.events.diagnostics.queues import AbstractQueueDiagnosticsCollector
from app.events.diagnostics.scheduler import AbstractSchedulerDiagnosticsCollector
from app.events.diagnostics.workers import AbstractWorkerDiagnosticsCollector
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractRuntimeSnapshotGenerator(ABC):
    """
    Abstract interface for generating consistent runtime snapshots.
    """

    @abstractmethod
    async def generate_snapshot(
        self,
        session: Optional[Any] = None,
    ) -> RuntimeSnapshot:
        """
        Generates a point-in-time consistent snapshot across all subsystems.
        """
        pass


class DefaultRuntimeSnapshotGenerator(AbstractRuntimeSnapshotGenerator):
    """
    Production-grade runtime snapshot generator.
    Enforces a single logical observation point (snapshot_id and snapshot_timestamp)
    and collects subsystem state concurrently with failure isolation.
    """

    def __init__(
        self,
        worker_collector: AbstractWorkerDiagnosticsCollector,
        dispatcher_collector: AbstractDispatcherDiagnosticsCollector,
        queue_collector: AbstractQueueDiagnosticsCollector,
        partition_collector: AbstractPartitionDiagnosticsCollector,
        lock_collector: AbstractLockDiagnosticsCollector,
        consumer_collector: AbstractConsumerDiagnosticsCollector,
        scheduler_collector: AbstractSchedulerDiagnosticsCollector,
        health_monitor: AbstractRuntimeHealthMonitor,
        config: Optional[DiagnosticsConfig] = None,
    ):
        self.worker_collector = worker_collector
        self.dispatcher_collector = dispatcher_collector
        self.queue_collector = queue_collector
        self.partition_collector = partition_collector
        self.lock_collector = lock_collector
        self.consumer_collector = consumer_collector
        self.scheduler_collector = scheduler_collector
        self.health_monitor = health_monitor
        self.config = config or DiagnosticsConfig()

    async def generate_snapshot(
        self,
        session: Optional[Any] = None,
    ) -> RuntimeSnapshot:
        # Step 1: Establish the single logical observation point
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        snapshot_timestamp = datetime.now(timezone.utc)
        start_time = time.monotonic()

        # Step 2: Concurrently query all subsystem collectors
        try:
            (
                workers_res,
                dispatchers_res,
                queues_res,
                partitions_res,
                locks_res,
                consumers_res,
                scheduler_res,
            ) = await asyncio.gather(
                self.worker_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.dispatcher_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.queue_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.partition_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.lock_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.consumer_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                self.scheduler_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session),
                return_exceptions=False,
            )
        except Exception as exc:
            logger.error(f"[RuntimeSnapshot] Subsystem collection failure: {exc}", exc_info=True)
            # Re-collect with fallback
            workers_res = await self.worker_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            dispatchers_res = await self.dispatcher_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            queues_res = await self.queue_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            partitions_res = await self.partition_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            locks_res = await self.lock_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            consumers_res = await self.consumer_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
            scheduler_res = await self.scheduler_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)

        # Step 3: Compute unified runtime health using the collected subsystem states
        health_res = await self.health_monitor.compute_health(
            snapshot_id=snapshot_id,
            snapshot_timestamp=snapshot_timestamp,
            workers=workers_res,
            dispatchers=dispatchers_res,
            queues=queues_res,
            partitions=partitions_res,
            locks=locks_res,
            consumers=consumers_res,
            scheduler=scheduler_res,
        )

        observation_window_ms = (time.monotonic() - start_time) * 1000.0

        # Step 4: Record observability metrics
        event_metrics.record_runtime_snapshot_request()

        return RuntimeSnapshot(
            snapshot_id=snapshot_id,
            snapshot_timestamp=snapshot_timestamp,
            observation_window_ms=round(observation_window_ms, 2),
            workers=workers_res,
            dispatchers=dispatchers_res,
            queues=queues_res,
            partitions=partitions_res,
            locks=locks_res,
            consumers=consumers_res,
            scheduler=scheduler_res,
            health=health_res,
        )
