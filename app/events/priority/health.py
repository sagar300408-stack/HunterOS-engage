"""
HunterOS Engage — Queue Health Monitoring Engine
app/events/priority/health.py

Tracks queue metrics, compute composite health scores (0..100), and classifies
system load state into NORMAL, BUSY, HIGH_LOAD, or SATURATED.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.events.observability.metrics import event_metrics
from app.events.priority.config import PriorityConfig
from app.events.priority.priority import PriorityLevel, PriorityResolver
from app.events.store.models import EventRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueueHealthSnapshot:
    """
    Point-in-time snapshot of queue health, throughput, latency, and load distribution.
    """
    queue_depth: int
    dispatch_rate: float
    completion_rate: float
    retry_rate: float
    dead_letter_rate: float
    worker_utilization: float
    oldest_pending_age_seconds: float
    oldest_retry_age_seconds: float
    partition_backlog: int
    priority_distribution: Dict[str, int]
    health_score: float
    system_load_state: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_depth": self.queue_depth,
            "dispatch_rate": round(self.dispatch_rate, 2),
            "completion_rate": round(self.completion_rate, 2),
            "retry_rate": round(self.retry_rate, 4),
            "dead_letter_rate": round(self.dead_letter_rate, 4),
            "worker_utilization": round(self.worker_utilization, 2),
            "oldest_pending_age_seconds": round(self.oldest_pending_age_seconds, 2),
            "oldest_retry_age_seconds": round(self.oldest_retry_age_seconds, 2),
            "partition_backlog": self.partition_backlog,
            "priority_distribution": self.priority_distribution,
            "health_score": round(self.health_score, 1),
            "system_load_state": self.system_load_state,
            "timestamp": self.timestamp.isoformat(),
        }


class QueueHealthMonitor:
    """
    Thread-safe Queue Health Monitor.
    Calculates operational health scores and load states from candidate batches and pipeline telemetry.
    """

    def __init__(self, config: Optional[PriorityConfig] = None):
        self.config = config or PriorityConfig.from_env()
        self._lock = threading.Lock()
        self._last_snapshot: Optional[QueueHealthSnapshot] = None

    def compute_snapshot(
        self,
        candidate_records: List[EventRecord],
        now: Optional[datetime] = None,
    ) -> QueueHealthSnapshot:
        """
        Computes a comprehensive health snapshot from pending candidate records and global telemetry.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        snapshot_metrics = event_metrics.get_snapshot()

        queue_depth = len(candidate_records)
        priority_counts: Dict[str, int] = {p.value: 0 for p in PriorityLevel}
        active_partitions = set()

        oldest_pending_age = 0.0
        oldest_retry_age = 0.0

        for r in candidate_records:
            # Partition backlog tracking
            if r.partition_key:
                active_partitions.add(r.partition_key)

            # Priority distribution
            prio = PriorityResolver.resolve_priority(r)
            priority_counts[prio.value] = priority_counts.get(prio.value, 0) + 1

            # Age calculation
            if r.occurred_at:
                occ = r.occurred_at
                if occ.tzinfo is None:
                    occ = occ.replace(tzinfo=timezone.utc)
                age = max(0.0, (now - occ).total_seconds())

                if r.lifecycle_state == "RETRYING":
                    if age > oldest_retry_age:
                        oldest_retry_age = age
                else:
                    if age > oldest_pending_age:
                        oldest_pending_age = age

        # Telemetry rates
        total_events = snapshot_metrics.events_processed + snapshot_metrics.events_failed
        dead_letter_rate = (
            snapshot_metrics.events_dead_lettered / total_events if total_events > 0 else 0.0
        )
        retry_rate = (
            snapshot_metrics.events_retried / total_events if total_events > 0 else 0.0
        )

        # Worker utilization estimate from active processing gauge
        # Normalizes active processing against a baseline concurrency pool (e.g. 10 workers)
        active_workers = snapshot_metrics.events_active_processing
        worker_utilization = min(1.0, active_workers / 10.0) if active_workers > 0 else 0.0

        # Load State Classification
        load_state = self._determine_load_state(queue_depth, worker_utilization)

        # Health Score Computation (0..100)
        health_score = self._compute_health_score(
            queue_depth=queue_depth,
            oldest_age=oldest_pending_age,
            dead_letter_rate=dead_letter_rate,
            worker_utilization=worker_utilization,
        )

        snapshot = QueueHealthSnapshot(
            queue_depth=queue_depth,
            dispatch_rate=float(snapshot_metrics.dispatcher_cycles),
            completion_rate=float(snapshot_metrics.events_processed),
            retry_rate=retry_rate,
            dead_letter_rate=dead_letter_rate,
            worker_utilization=worker_utilization,
            oldest_pending_age_seconds=oldest_pending_age,
            oldest_retry_age_seconds=oldest_retry_age,
            partition_backlog=len(active_partitions),
            priority_distribution=priority_counts,
            health_score=health_score,
            system_load_state=load_state,
            timestamp=now,
        )

        with self._lock:
            self._last_snapshot = snapshot

        # Update telemetry gauges
        event_metrics.set("dispatcher_queue_depth", queue_depth)
        event_metrics.set("queue_health_score", int(health_score))
        event_metrics.set("worker_utilization", int(worker_utilization * 100))

        return snapshot

    def get_latest_snapshot(self) -> Optional[QueueHealthSnapshot]:
        with self._lock:
            return self._last_snapshot

    def _determine_load_state(self, queue_depth: int, worker_utilization: float) -> str:
        if (
            queue_depth >= self.config.queue_depth_saturated_threshold
            or worker_utilization >= 0.98
        ):
            return "SATURATED"
        if (
            queue_depth >= self.config.queue_depth_high_load_threshold
            or worker_utilization >= self.config.max_worker_utilization_ratio
        ):
            return "HIGH_LOAD"
        if (
            queue_depth >= self.config.queue_depth_busy_threshold
            or worker_utilization >= 0.65
        ):
            return "BUSY"
        return "NORMAL"

    def _compute_health_score(
        self,
        queue_depth: int,
        oldest_age: float,
        dead_letter_rate: float,
        worker_utilization: float,
    ) -> float:
        """
        Calculates a composite health score between 0.0 and 100.0.
        """
        score = 100.0

        # Queue depth penalty (up to 30 points)
        if queue_depth > self.config.queue_depth_normal_threshold:
            depth_ratio = min(
                1.0,
                (queue_depth - self.config.queue_depth_normal_threshold)
                / max(1, self.config.queue_depth_saturated_threshold),
            )
            score -= depth_ratio * 30.0

        # Oldest pending event latency penalty (up to 30 points)
        if oldest_age > 30.0:
            age_ratio = min(1.0, (oldest_age - 30.0) / 120.0)
            score -= age_ratio * 30.0

        # Dead letter / failure penalty (up to 20 points)
        score -= min(20.0, dead_letter_rate * 200.0)

        # Worker saturation penalty (up to 20 points)
        if worker_utilization > 0.85:
            score -= (worker_utilization - 0.85) / 0.15 * 20.0

        return max(0.0, min(100.0, score))
