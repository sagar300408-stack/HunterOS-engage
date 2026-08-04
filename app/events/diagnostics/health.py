"""
HunterOS Engage — Runtime Health Monitor
app/events/diagnostics/health.py

Computes overall runtime health, multi-dimensional subsystem scores,
resource utilization, capacity estimation, and early warning anomaly indicators.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import (
    ConsumerDiagnostics,
    DispatcherDiagnostics,
    EarlyWarningIndicator,
    LockDiagnostics,
    PartitionDiagnostics,
    QueueDiagnostics,
    RuntimeHealthStatus,
    RuntimeHealthSummary,
    SchedulerDiagnostics,
    SubsystemHealthStatus,
    SubsystemType,
    WorkerDiagnostics,
)
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractRuntimeHealthMonitor(ABC):
    """
    Abstract interface for runtime health monitoring.
    """

    @abstractmethod
    async def compute_health(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        workers: WorkerDiagnostics,
        dispatchers: DispatcherDiagnostics,
        queues: QueueDiagnostics,
        partitions: PartitionDiagnostics,
        locks: LockDiagnostics,
        consumers: ConsumerDiagnostics,
        scheduler: SchedulerDiagnostics,
    ) -> RuntimeHealthSummary:
        """
        Computes multi-dimensional runtime health across all subsystem states.
        """
        pass


class DefaultRuntimeHealthMonitor(AbstractRuntimeHealthMonitor):
    """
    Production-grade runtime health monitor.
    Applies weighted scoring, threshold detection, and early warning generation.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or DiagnosticsConfig()

    async def compute_health(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        workers: WorkerDiagnostics,
        dispatchers: DispatcherDiagnostics,
        queues: QueueDiagnostics,
        partitions: PartitionDiagnostics,
        locks: LockDiagnostics,
        consumers: ConsumerDiagnostics,
        scheduler: SchedulerDiagnostics,
    ) -> RuntimeHealthSummary:
        warnings: List[EarlyWarningIndicator] = []
        subsystems: Dict[str, SubsystemHealthStatus] = {}

        # ── 1. Evaluate Workers Subsystem ────────────────────────────────────
        w_score = 100
        w_reasons: List[str] = []
        if workers.worker_failures_count > 0:
            penalty = min(30, workers.worker_failures_count * 5)
            w_score -= penalty
            w_reasons.append(f"{workers.worker_failures_count} worker task failure(s) recorded")
        if workers.worker_utilization_pct >= 95.0:
            w_score -= 20
            w_reasons.append(f"Worker saturation high ({workers.worker_utilization_pct}%)")
            warnings.append(
                EarlyWarningIndicator(
                    warning_id=f"warn_{uuid.uuid4().hex[:8]}",
                    subsystem=SubsystemType.WORKERS,
                    severity="WARNING",
                    message="High worker pool utilization detected",
                    metric_name="worker_utilization_pct",
                    current_value=workers.worker_utilization_pct,
                    threshold_value=95.0,
                    recommended_action="Scale Celery/background worker capacity",
                )
            )

        w_status = RuntimeHealthStatus.HEALTHY
        if w_score < self.config.health_critical_threshold:
            w_status = RuntimeHealthStatus.CRITICAL
        elif w_score < self.config.health_warning_threshold:
            w_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.WORKERS.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.WORKERS,
            score=max(0, w_score),
            status=w_status,
            reasons=w_reasons,
        )

        # ── 2. Evaluate Dispatchers Subsystem ────────────────────────────────
        d_score = 100
        d_reasons: List[str] = []
        if dispatchers.active_dispatchers_count == 0:
            d_score -= 80
            d_reasons.append("No active dispatchers running")
            warnings.append(
                EarlyWarningIndicator(
                    warning_id=f"warn_{uuid.uuid4().hex[:8]}",
                    subsystem=SubsystemType.DISPATCHERS,
                    severity="CRITICAL",
                    message="Zero active dispatchers detected",
                    metric_name="active_dispatchers_count",
                    current_value=0.0,
                    threshold_value=1.0,
                    recommended_action="Restart outbox dispatcher service immediately",
                )
            )
        if dispatchers.outbox_queue_depth > self.config.queue_high_watermark:
            d_score -= 25
            d_reasons.append(f"Outbox queue depth high ({dispatchers.outbox_queue_depth})")

        d_status = RuntimeHealthStatus.HEALTHY
        if d_score < self.config.health_critical_threshold:
            d_status = RuntimeHealthStatus.CRITICAL
        elif d_score < self.config.health_warning_threshold:
            d_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.DISPATCHERS.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.DISPATCHERS,
            score=max(0, d_score),
            status=d_status,
            reasons=d_reasons,
        )

        # ── 3. Evaluate Queues Subsystem ─────────────────────────────────────
        q_score = 100
        q_reasons: List[str] = []
        if queues.dead_letter_rate > 5.0:
            q_score -= min(50, int(queues.dead_letter_rate * 5))
            q_reasons.append(f"Elevated dead-letter rate ({queues.dead_letter_rate}%)")
            warnings.append(
                EarlyWarningIndicator(
                    warning_id=f"warn_{uuid.uuid4().hex[:8]}",
                    subsystem=SubsystemType.QUEUES,
                    severity="CRITICAL" if queues.dead_letter_rate > 20.0 else "WARNING",
                    message="Elevated dead-letter transition rate",
                    metric_name="dead_letter_rate",
                    current_value=queues.dead_letter_rate,
                    threshold_value=5.0,
                    recommended_action="Inspect consumer exceptions and verify event schemas",
                )
            )
        if queues.total_depth > self.config.queue_high_watermark:
            q_score -= 20
            q_reasons.append(f"Queue depth exceeds watermark ({queues.total_depth})")

        q_status = RuntimeHealthStatus.HEALTHY
        if q_score < self.config.health_critical_threshold:
            q_status = RuntimeHealthStatus.CRITICAL
        elif q_score < self.config.health_warning_threshold:
            q_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.QUEUES.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.QUEUES,
            score=max(0, q_score),
            status=q_status,
            reasons=q_reasons,
        )

        # ── 4. Evaluate Partitions Subsystem ─────────────────────────────────
        p_score = 100
        p_reasons: List[str] = []
        if partitions.waiting_partitions_count > partitions.active_partitions_count:
            p_score -= 20
            p_reasons.append(f"More waiting partitions ({partitions.waiting_partitions_count}) than active")
        if partitions.oldest_event_age_sec > 60.0:
            p_score -= 15
            p_reasons.append(f"Oldest event age elevated ({partitions.oldest_event_age_sec}s)")

        p_status = RuntimeHealthStatus.HEALTHY
        if p_score < self.config.health_critical_threshold:
            p_status = RuntimeHealthStatus.CRITICAL
        elif p_score < self.config.health_warning_threshold:
            p_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.PARTITIONS.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.PARTITIONS,
            score=max(0, p_score),
            status=p_status,
            reasons=p_reasons,
        )

        # ── 5. Evaluate Locks Subsystem ──────────────────────────────────────
        l_score = 100
        l_reasons: List[str] = []
        if locks.lock_contention_events_total > 50:
            l_score -= 15
            l_reasons.append(f"High lock contention ({locks.lock_contention_events_total} conflicts)")

        l_status = RuntimeHealthStatus.HEALTHY
        if l_score < self.config.health_critical_threshold:
            l_status = RuntimeHealthStatus.CRITICAL
        elif l_score < self.config.health_warning_threshold:
            l_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.LOCKS.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.LOCKS,
            score=max(0, l_score),
            status=l_status,
            reasons=l_reasons,
        )

        # ── 6. Evaluate Consumers Subsystem ──────────────────────────────────
        c_score = 100
        c_reasons: List[str] = []
        if consumers.overall_average_latency_ms > self.config.consumer_slow_threshold_ms:
            c_score -= 20
            c_reasons.append(f"High average consumer latency ({consumers.overall_average_latency_ms}ms)")
        if consumers.total_failures > 0:
            fail_rate = (consumers.total_failures / consumers.total_executions * 100.0) if consumers.total_executions > 0 else 0.0
            if fail_rate > 10.0:
                c_score -= min(40, int(fail_rate * 2))
                c_reasons.append(f"Consumer failure rate elevated ({fail_rate:.1f}%)")

        c_status = RuntimeHealthStatus.HEALTHY
        if c_score < self.config.health_critical_threshold:
            c_status = RuntimeHealthStatus.CRITICAL
        elif c_score < self.config.health_warning_threshold:
            c_status = RuntimeHealthStatus.DEGRADED

        subsystems[SubsystemType.CONSUMERS.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.CONSUMERS,
            score=max(0, c_score),
            status=c_status,
            reasons=c_reasons,
        )

        # ── 7. Evaluate Scheduler Subsystem ──────────────────────────────────
        s_score = 100
        s_reasons: List[str] = []
        subsystems[SubsystemType.SCHEDULER.value] = SubsystemHealthStatus(
            subsystem=SubsystemType.SCHEDULER,
            score=s_score,
            status=RuntimeHealthStatus.HEALTHY,
            reasons=s_reasons,
        )

        # ── Overall Weighted Score ───────────────────────────────────────────
        weights = {
            SubsystemType.QUEUES.value: 0.25,
            SubsystemType.WORKERS.value: 0.20,
            SubsystemType.DISPATCHERS.value: 0.20,
            SubsystemType.CONSUMERS.value: 0.15,
            SubsystemType.PARTITIONS.value: 0.10,
            SubsystemType.LOCKS.value: 0.05,
            SubsystemType.SCHEDULER.value: 0.05,
        }

        overall_score = sum(subsystems[k].score * w for k, w in weights.items())
        final_score = int(round(overall_score))

        overall_status = RuntimeHealthStatus.HEALTHY
        if final_score < self.config.health_critical_threshold:
            overall_status = RuntimeHealthStatus.CRITICAL
        elif final_score < self.config.health_warning_threshold:
            overall_status = RuntimeHealthStatus.DEGRADED

        # Resource utilization summary
        res_util = {
            "worker_utilization_pct": workers.worker_utilization_pct,
            "queue_depth": float(queues.total_depth),
            "active_partitions": float(partitions.active_partitions_count),
            "active_locks": float(locks.active_locks_count),
        }

        # Capacity estimation
        capacity = {
            "estimated_max_events_per_sec": round(workers.total_workers * 50.0, 1),
            "current_throughput_per_sec": queues.throughput_per_sec,
            "headroom_pct": round(max(0.0, 100.0 - workers.worker_utilization_pct), 1),
        }

        event_metrics.record_health_check()

        return RuntimeHealthSummary(
            snapshot_id=snapshot_id,
            snapshot_timestamp=snapshot_timestamp,
            overall_score=final_score,
            overall_status=overall_status,
            subsystem_health=subsystems,
            resource_utilization=res_util,
            capacity_estimation=capacity,
            early_warning_indicators=warnings,
        )
