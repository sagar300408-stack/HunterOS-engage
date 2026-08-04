"""
HunterOS Engage — Live Inspection Service
app/events/diagnostics/inspection.py

Provides on-demand targeted live inspection across specific subsystems,
entities, and state filters without modifying execution state.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import (
    LiveInspectionQuery,
    LiveInspectionResult,
    SubsystemType,
)
from app.events.diagnostics.workers import AbstractWorkerDiagnosticsCollector
from app.events.diagnostics.dispatchers import AbstractDispatcherDiagnosticsCollector
from app.events.diagnostics.partitions import AbstractPartitionDiagnosticsCollector
from app.events.diagnostics.locks import AbstractLockDiagnosticsCollector
from app.events.diagnostics.consumers import AbstractConsumerDiagnosticsCollector
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractLiveInspectionService(ABC):
    """
    Abstract interface for targeted live subsystem inspection.
    """

    @abstractmethod
    async def inspect(
        self,
        query: LiveInspectionQuery,
        session: Optional[Any] = None,
    ) -> LiveInspectionResult:
        """
        Executes a targeted inspection query.
        """
        pass


class DefaultLiveInspectionService(AbstractLiveInspectionService):
    """
    Production-grade live inspection service with targeted filters.
    """

    def __init__(
        self,
        worker_collector: AbstractWorkerDiagnosticsCollector,
        dispatcher_collector: AbstractDispatcherDiagnosticsCollector,
        partition_collector: AbstractPartitionDiagnosticsCollector,
        lock_collector: AbstractLockDiagnosticsCollector,
        consumer_collector: AbstractConsumerDiagnosticsCollector,
        config: Optional[DiagnosticsConfig] = None,
    ):
        self.worker_collector = worker_collector
        self.dispatcher_collector = dispatcher_collector
        self.partition_collector = partition_collector
        self.lock_collector = lock_collector
        self.consumer_collector = consumer_collector
        self.config = config or DiagnosticsConfig()

    async def inspect(
        self,
        query: LiveInspectionQuery,
        session: Optional[Any] = None,
    ) -> LiveInspectionResult:
        snapshot_id = f"insp_{uuid.uuid4().hex[:12]}"
        snapshot_timestamp = datetime.now(timezone.utc)
        details: List[Dict[str, Any]] = []

        try:
            if query.subsystem == SubsystemType.WORKERS:
                res = await self.worker_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
                for w in res.workers:
                    if query.entity_id and w.worker_id != query.entity_id:
                        continue
                    if query.filter_state and w.status.lower() != query.filter_state.lower():
                        continue
                    details.append(w.model_dump())

            elif query.subsystem == SubsystemType.DISPATCHERS:
                res = await self.dispatcher_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
                for d in res.dispatchers:
                    if query.entity_id and d.dispatcher_id != query.entity_id:
                        continue
                    if query.filter_state and d.status.lower() != query.filter_state.lower():
                        continue
                    details.append(d.model_dump())

            elif query.subsystem == SubsystemType.PARTITIONS:
                res = await self.partition_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
                for p in res.partitions:
                    if query.entity_id and p.partition_key != query.entity_id:
                        continue
                    if query.filter_state and p.state.lower() != query.filter_state.lower():
                        continue
                    details.append(p.model_dump())

            elif query.subsystem == SubsystemType.LOCKS:
                res = await self.lock_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
                for l in res.locks:
                    if query.entity_id and l.resource_id != query.entity_id:
                        continue
                    if query.filter_state:
                        if query.filter_state.lower() == "expired" and not l.is_expired:
                            continue
                        if query.filter_state.lower() == "active" and l.is_expired:
                            continue
                    details.append(l.model_dump())

            elif query.subsystem == SubsystemType.CONSUMERS:
                res = await self.consumer_collector.collect_diagnostics(snapshot_id, snapshot_timestamp, session)
                for c in res.consumers:
                    if query.entity_id and c.consumer_name != query.entity_id:
                        continue
                    details.append(c.model_dump())

            event_metrics.record_diagnostic_query()

            matched = details[: query.limit]
            return LiveInspectionResult(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                subsystem=query.subsystem,
                matched_count=len(matched),
                details=matched,
            )
        except Exception as exc:
            logger.error(f"[LiveInspection] Inspection error for {query.subsystem}: {exc}", exc_info=True)
            return LiveInspectionResult(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                subsystem=query.subsystem,
                matched_count=0,
                details=[],
            )
