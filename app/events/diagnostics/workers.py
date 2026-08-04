"""
HunterOS Engage — Worker Diagnostics Collector
app/events/diagnostics/workers.py

Passive operational diagnostics collector for background workers,
executing events, utilization, durations, and throughput.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import WorkerDetail, WorkerDiagnostics
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractWorkerDiagnosticsCollector(ABC):
    """
    Abstract interface for worker diagnostics collection.
    """

    @abstractmethod
    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> WorkerDiagnostics:
        """
        Collects point-in-time diagnostics for all registered/active workers.
        """
        pass


class DefaultWorkerDiagnosticsCollector(AbstractWorkerDiagnosticsCollector):
    """
    Production-grade passive worker diagnostics collector.
    Inspects process-local worker registries, thread states, and metrics.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or DiagnosticsConfig()
        self._lock = threading.Lock()
        self._workers: Dict[str, WorkerDetail] = {}

    def record_worker_heartbeat(
        self,
        worker_id: str,
        status: str = "IDLE",
        current_task_id: Optional[str] = None,
        current_event_id: Optional[str] = None,
        current_partition_key: Optional[str] = None,
        execution_duration_ms: Optional[float] = None,
        completed_delta: int = 0,
        failed_delta: int = 0,
    ) -> None:
        """
        Thread-safe method for workers to report status without blocking execution.
        """
        try:
            with self._lock:
                now = datetime.now(timezone.utc)
                if worker_id not in self._workers:
                    self._workers[worker_id] = WorkerDetail(
                        worker_id=worker_id,
                        status=status,
                        current_task_id=current_task_id,
                        current_event_id=current_event_id,
                        current_partition_key=current_partition_key,
                        execution_duration_ms=execution_duration_ms,
                        total_completed_tasks=completed_delta,
                        total_failed_tasks=failed_delta,
                        last_heartbeat=now,
                    )
                else:
                    w = self._workers[worker_id]
                    w.status = status
                    w.current_task_id = current_task_id
                    w.current_event_id = current_event_id
                    w.current_partition_key = current_partition_key
                    w.execution_duration_ms = execution_duration_ms
                    w.total_completed_tasks += completed_delta
                    w.total_failed_tasks += failed_delta
                    w.last_heartbeat = now
        except Exception as exc:
            logger.debug(f"[WorkerDiagnostics] Failed to record worker heartbeat: {exc}")

    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> WorkerDiagnostics:
        try:
            now = snapshot_timestamp
            with self._lock:
                worker_list: List[WorkerDetail] = []
                for w_id, w in list(self._workers.items()):
                    # Mark stale workers as IDLE or TERMINATED if heartbeat expired
                    if w.last_heartbeat:
                        age = (now - w.last_heartbeat).total_seconds()
                        if age > self.config.worker_stale_threshold_seconds and w.status != "TERMINATED":
                            w.status = "IDLE"
                            w.current_task_id = None
                            w.current_event_id = None
                    worker_list.append(w.model_copy())

            # Fallback/baseline if no explicit workers registered
            if not worker_list:
                worker_list = [
                    WorkerDetail(
                        worker_id="worker_default_0",
                        status="IDLE",
                        last_heartbeat=now,
                    )
                ]

            total_workers = len(worker_list)
            active_workers = sum(1 for w in worker_list if w.status in ("ACTIVE", "BUSY"))
            idle_workers = total_workers - active_workers
            executing_count = sum(1 for w in worker_list if w.current_event_id is not None)

            # Get metrics snapshot for throughput & failure aggregates
            m_snap = event_metrics.snapshot()
            executing_count = max(executing_count, m_snap.events_active_processing)

            worker_utilization = (active_workers / total_workers * 100.0) if total_workers > 0 else 0.0
            event_metrics.set_worker_utilization(int(worker_utilization))

            durations = [w.execution_duration_ms for w in worker_list if w.execution_duration_ms is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            total_completed = sum(w.total_completed_tasks for w in worker_list) or m_snap.events_processed
            total_failed = sum(w.total_failed_tasks for w in worker_list) or m_snap.events_failed

            status = "HEALTHY"
            if total_workers > 0 and worker_utilization >= 95.0:
                status = "DEGRADED"

            return WorkerDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                status=status,
                total_workers=total_workers,
                active_workers=active_workers,
                idle_workers=idle_workers,
                executing_events_count=executing_count,
                worker_utilization_pct=round(worker_utilization, 2),
                average_execution_duration_ms=round(avg_duration, 2),
                worker_throughput_per_sec=round(float(total_completed), 2),
                worker_failures_count=total_failed,
                workers=worker_list[: self.config.max_inspected_items],
            )
        except Exception as exc:
            logger.error(f"[WorkerDiagnostics] Error collecting worker diagnostics: {exc}", exc_info=True)
            return WorkerDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                status="DEGRADED",
                total_workers=1,
                active_workers=0,
                idle_workers=1,
            )
