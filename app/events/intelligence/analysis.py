"""
HunterOS Engage — Historical Analytics Engine
app/events/intelligence/analysis.py

Maintains rolling historical statistics, latency percentiles (P50, P90, P95, P99),
failure/retry rates, consumer latency breakdowns, and partition distributions.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import SpanStatus


@dataclass
class HistoricalTrends:
    """
    Rolling performance statistics and percentiles across completed traces.
    """
    total_traces: int = 0
    completed_traces: int = 0
    failed_traces: int = 0
    failure_rate: float = 0.0
    retry_rate: float = 0.0
    dead_letter_rate: float = 0.0

    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p90_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0

    consumer_latency_trends: Dict[str, Dict[str, float]] = field(default_factory=dict)
    partition_distribution: Dict[str, int] = field(default_factory=dict)
    worker_distribution: Dict[str, int] = field(default_factory=dict)
    dispatcher_distribution: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_traces": self.total_traces,
            "completed_traces": self.completed_traces,
            "failed_traces": self.failed_traces,
            "failure_rate": round(self.failure_rate, 4),
            "retry_rate": round(self.retry_rate, 4),
            "dead_letter_rate": round(self.dead_letter_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 3),
            "min_duration_ms": round(self.min_duration_ms, 3),
            "max_duration_ms": round(self.max_duration_ms, 3),
            "p50_duration_ms": round(self.p50_duration_ms, 3),
            "p90_duration_ms": round(self.p90_duration_ms, 3),
            "p95_duration_ms": round(self.p95_duration_ms, 3),
            "p99_duration_ms": round(self.p99_duration_ms, 3),
            "consumer_latency_trends": self.consumer_latency_trends,
            "partition_distribution": self.partition_distribution,
            "worker_distribution": self.worker_distribution,
            "dispatcher_distribution": self.dispatcher_distribution,
            "timestamp": self.timestamp.isoformat(),
        }


class HistoricalAnalyticsEngine:
    """
    Computes statistical summaries and latency percentiles from completed trace snapshots.
    """

    @staticmethod
    def calculate_trends(snapshots: List[TraceSnapshot]) -> HistoricalTrends:
        if not snapshots:
            return HistoricalTrends()

        total = len(snapshots)
        durations: List[float] = []
        failed_count = 0
        retry_count = 0
        dead_letter_count = 0

        consumer_latencies: Dict[str, List[float]] = defaultdict(list)
        partition_dist: Dict[str, int] = defaultdict(int)
        worker_dist: Dict[str, int] = defaultdict(int)
        dispatcher_dist: Dict[str, int] = defaultdict(int)

        for s in snapshots:
            root = s.root_span
            if not root:
                continue

            if root.status == SpanStatus.FAILED:
                failed_count += 1

            if root.duration_ms is not None:
                durations.append(root.duration_ms)

            if s.retry_history:
                retry_count += len(s.retry_history)

            ctx = root.context
            if ctx:
                if ctx.partition_key:
                    partition_dist[ctx.partition_key] += 1
                if ctx.worker_id:
                    worker_dist[ctx.worker_id] += 1
                if ctx.dispatcher_id:
                    dispatcher_dist[ctx.dispatcher_id] += 1

            for span in s.spans:
                if "consumer" in span.component.lower() and span.duration_ms is not None:
                    consumer_latencies[span.component].append(span.duration_ms)
                if "dead_letter" in span.metadata or "dead_letter" in str(span.error).lower():
                    dead_letter_count += 1

        durations.sort()
        n = len(durations)

        avg_dur = sum(durations) / n if n > 0 else 0.0
        min_dur = durations[0] if n > 0 else 0.0
        max_dur = durations[-1] if n > 0 else 0.0

        p50 = durations[int(0.50 * (n - 1))] if n > 0 else 0.0
        p90 = durations[int(0.90 * (n - 1))] if n > 0 else 0.0
        p95 = durations[int(0.95 * (n - 1))] if n > 0 else 0.0
        p99 = durations[int(0.99 * (n - 1))] if n > 0 else 0.0

        consumer_trends: Dict[str, Dict[str, float]] = {}
        for comp, lats in consumer_latencies.items():
            if lats:
                lats.sort()
                consumer_trends[comp] = {
                    "count": len(lats),
                    "avg_ms": round(sum(lats) / len(lats), 3),
                    "p95_ms": round(lats[int(0.95 * (len(lats) - 1))], 3),
                    "max_ms": round(lats[-1], 3),
                }

        return HistoricalTrends(
            total_traces=total,
            completed_traces=total - failed_count,
            failed_traces=failed_count,
            failure_rate=failed_count / total if total > 0 else 0.0,
            retry_rate=retry_count / total if total > 0 else 0.0,
            dead_letter_rate=dead_letter_count / total if total > 0 else 0.0,
            avg_duration_ms=avg_dur,
            min_duration_ms=min_dur,
            max_duration_ms=max_dur,
            p50_duration_ms=p50,
            p90_duration_ms=p90,
            p95_duration_ms=p95,
            p99_duration_ms=p99,
            consumer_latency_trends=consumer_trends,
            partition_distribution=dict(partition_dist),
            worker_distribution=dict(worker_dist),
            dispatcher_distribution=dict(dispatcher_dist),
        )
