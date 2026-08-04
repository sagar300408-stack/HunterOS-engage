"""
HunterOS Engage — Runtime Diagnostics Engine
app/events/diagnostics/engine.py

Central orchestration engine coordinating live runtime inspection,
subsystem diagnostics collectors, health monitors, and consistent snapshot generation.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.consumers import (
    AbstractConsumerDiagnosticsCollector,
    DefaultConsumerDiagnosticsCollector,
)
from app.events.diagnostics.dispatchers import (
    AbstractDispatcherDiagnosticsCollector,
    DefaultDispatcherDiagnosticsCollector,
)
from app.events.diagnostics.health import (
    AbstractRuntimeHealthMonitor,
    DefaultRuntimeHealthMonitor,
)
from app.events.diagnostics.inspection import (
    AbstractLiveInspectionService,
    DefaultLiveInspectionService,
)
from app.events.diagnostics.locks import (
    AbstractLockDiagnosticsCollector,
    DefaultLockDiagnosticsCollector,
)
from app.events.diagnostics.models import (
    ConsumerDiagnostics,
    DispatcherDiagnostics,
    LiveInspectionQuery,
    LiveInspectionResult,
    LockDiagnostics,
    PartitionDiagnostics,
    QueueDiagnostics,
    RuntimeHealthSummary,
    RuntimeSnapshot,
    SchedulerDiagnostics,
    WorkerDiagnostics,
)
from app.events.diagnostics.partitions import (
    AbstractPartitionDiagnosticsCollector,
    DefaultPartitionDiagnosticsCollector,
)
from app.events.diagnostics.queues import (
    AbstractQueueDiagnosticsCollector,
    DefaultQueueDiagnosticsCollector,
)
from app.events.diagnostics.runtime import (
    AbstractRuntimeSnapshotGenerator,
    DefaultRuntimeSnapshotGenerator,
)
from app.events.diagnostics.scheduler import (
    AbstractSchedulerDiagnosticsCollector,
    DefaultSchedulerDiagnosticsCollector,
)
from app.events.diagnostics.workers import (
    AbstractWorkerDiagnosticsCollector,
    DefaultWorkerDiagnosticsCollector,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractDiagnosticsEngine(ABC):
    """
    Abstract interface for the central Runtime Diagnostics Engine.
    """

    @abstractmethod
    async def get_runtime_snapshot(self, session: Optional[Any] = None) -> RuntimeSnapshot:
        """Generates a complete, point-in-time runtime snapshot."""
        pass

    @abstractmethod
    async def get_worker_diagnostics(self, session: Optional[Any] = None) -> WorkerDiagnostics:
        """Returns live worker subsystem diagnostics."""
        pass

    @abstractmethod
    async def get_dispatcher_diagnostics(self, session: Optional[Any] = None) -> DispatcherDiagnostics:
        """Returns live dispatcher subsystem diagnostics."""
        pass

    @abstractmethod
    async def get_queue_diagnostics(self, session: Optional[Any] = None) -> QueueDiagnostics:
        """Returns live queue & lifecycle distribution diagnostics."""
        pass

    @abstractmethod
    async def get_partition_diagnostics(self, session: Optional[Any] = None) -> PartitionDiagnostics:
        """Returns live partition subsystem diagnostics."""
        pass

    @abstractmethod
    async def get_lock_diagnostics(self, session: Optional[Any] = None) -> LockDiagnostics:
        """Returns live partition lock lease diagnostics."""
        pass

    @abstractmethod
    async def get_consumer_diagnostics(self, session: Optional[Any] = None) -> ConsumerDiagnostics:
        """Returns live consumer execution diagnostics."""
        pass

    @abstractmethod
    async def get_scheduler_diagnostics(self, session: Optional[Any] = None) -> SchedulerDiagnostics:
        """Returns live partition/priority scheduler diagnostics."""
        pass

    @abstractmethod
    async def get_runtime_health(self, session: Optional[Any] = None) -> RuntimeHealthSummary:
        """Returns runtime health evaluation and early warning alerts."""
        pass

    @abstractmethod
    async def inspect_subsystem(
        self, query: LiveInspectionQuery, session: Optional[Any] = None
    ) -> LiveInspectionResult:
        """Executes a targeted live inspection query."""
        pass


class DefaultDiagnosticsEngine(AbstractDiagnosticsEngine):
    """
    Production-grade implementation of the Runtime Diagnostics Engine.
    Coordinating all diagnostic collectors and snapshot generators.
    """

    def __init__(
        self,
        config: Optional[DiagnosticsConfig] = None,
        worker_collector: Optional[AbstractWorkerDiagnosticsCollector] = None,
        dispatcher_collector: Optional[AbstractDispatcherDiagnosticsCollector] = None,
        queue_collector: Optional[AbstractQueueDiagnosticsCollector] = None,
        partition_collector: Optional[AbstractPartitionDiagnosticsCollector] = None,
        lock_collector: Optional[AbstractLockDiagnosticsCollector] = None,
        consumer_collector: Optional[AbstractConsumerDiagnosticsCollector] = None,
        scheduler_collector: Optional[AbstractSchedulerDiagnosticsCollector] = None,
        health_monitor: Optional[AbstractRuntimeHealthMonitor] = None,
        snapshot_generator: Optional[AbstractRuntimeSnapshotGenerator] = None,
        inspection_service: Optional[AbstractLiveInspectionService] = None,
    ):
        self.config = config or DiagnosticsConfig.from_env()

        self.worker_collector = worker_collector or DefaultWorkerDiagnosticsCollector(self.config)
        self.dispatcher_collector = dispatcher_collector or DefaultDispatcherDiagnosticsCollector(self.config)
        self.queue_collector = queue_collector or DefaultQueueDiagnosticsCollector(self.config)
        self.partition_collector = partition_collector or DefaultPartitionDiagnosticsCollector(self.config)
        self.lock_collector = lock_collector or DefaultLockDiagnosticsCollector(self.config)
        self.consumer_collector = consumer_collector or DefaultConsumerDiagnosticsCollector(self.config)
        self.scheduler_collector = scheduler_collector or DefaultSchedulerDiagnosticsCollector(self.config)

        self.health_monitor = health_monitor or DefaultRuntimeHealthMonitor(self.config)

        self.snapshot_generator = snapshot_generator or DefaultRuntimeSnapshotGenerator(
            worker_collector=self.worker_collector,
            dispatcher_collector=self.dispatcher_collector,
            queue_collector=self.queue_collector,
            partition_collector=self.partition_collector,
            lock_collector=self.lock_collector,
            consumer_collector=self.consumer_collector,
            scheduler_collector=self.scheduler_collector,
            health_monitor=self.health_monitor,
            config=self.config,
        )

        self.inspection_service = inspection_service or DefaultLiveInspectionService(
            worker_collector=self.worker_collector,
            dispatcher_collector=self.dispatcher_collector,
            partition_collector=self.partition_collector,
            lock_collector=self.lock_collector,
            consumer_collector=self.consumer_collector,
            config=self.config,
        )

    def _generate_obs_point(self) -> tuple[str, datetime]:
        return f"snap_{uuid.uuid4().hex[:12]}", datetime.now(timezone.utc)

    async def get_runtime_snapshot(self, session: Optional[Any] = None) -> RuntimeSnapshot:
        return await self.snapshot_generator.generate_snapshot(session)

    async def get_worker_diagnostics(self, session: Optional[Any] = None) -> WorkerDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.worker_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_dispatcher_diagnostics(self, session: Optional[Any] = None) -> DispatcherDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.dispatcher_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_queue_diagnostics(self, session: Optional[Any] = None) -> QueueDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.queue_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_partition_diagnostics(self, session: Optional[Any] = None) -> PartitionDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.partition_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_lock_diagnostics(self, session: Optional[Any] = None) -> LockDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.lock_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_consumer_diagnostics(self, session: Optional[Any] = None) -> ConsumerDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.consumer_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_scheduler_diagnostics(self, session: Optional[Any] = None) -> SchedulerDiagnostics:
        s_id, s_ts = self._generate_obs_point()
        return await self.scheduler_collector.collect_diagnostics(s_id, s_ts, session)

    async def get_runtime_health(self, session: Optional[Any] = None) -> RuntimeHealthSummary:
        snap = await self.get_runtime_snapshot(session)
        return snap.health

    async def inspect_subsystem(
        self, query: LiveInspectionQuery, session: Optional[Any] = None
    ) -> LiveInspectionResult:
        return await self.inspection_service.inspect(query, session)
