"""
HunterOS Engage — Bottleneck Analyzer
app/events/intelligence/bottlenecks.py

Identifies execution bottlenecks, queue congestion, slow consumers,
dispatcher delays, database latency, and partition contention in completed traces.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    BottleneckCategory,
    BottleneckReport,
    SeverityLevel,
)
from app.events.tracing.snapshot import TraceSnapshot


class AbstractBottleneckAnalyzer(ABC):
    """
    Interface for bottleneck analyzers.
    """

    @abstractmethod
    def analyze_bottlenecks(self, snapshot: TraceSnapshot) -> List[BottleneckReport]:
        """
        Analyzes a completed trace snapshot and returns all identified bottlenecks.
        """
        pass


class DefaultBottleneckAnalyzer(AbstractBottleneckAnalyzer):
    """
    Standard production bottleneck analyzer.
    Evaluates absolute thresholds and relative percentage of trace duration.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def analyze_bottlenecks(self, snapshot: TraceSnapshot) -> List[BottleneckReport]:
        if not snapshot or not snapshot.spans:
            return []

        bottlenecks: List[BottleneckReport] = []
        total_duration = snapshot.root_span.duration_ms or 0.0
        if total_duration <= 0.0:
            return []

        ratio_threshold = self.config.component_bottleneck_ratio_threshold

        for span in snapshot.spans:
            dur = span.duration_ms or 0.0
            if dur <= 0.0:
                continue

            pct = (dur / total_duration) * 100.0 if total_duration > 0 else 0.0
            comp = span.component.lower()
            op = span.operation.lower()

            # 1. Slow Consumer
            if "consumer" in comp or "handle_event" in op:
                if dur >= self.config.slow_consumer_threshold_ms or (pct >= ratio_threshold * 100 and dur >= 50.0):
                    severity = SeverityLevel.HIGH if dur >= self.config.slow_consumer_threshold_ms * 2 else SeverityLevel.MEDIUM
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.SLOW_CONSUMER,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=severity,
                            impact_summary=f"Consumer {span.component} consumed {dur:.1f}ms ({pct:.1f}% of trace).",
                            evidence={"span_id": span.span_id, "threshold_ms": self.config.slow_consumer_threshold_ms},
                        )
                    )

            # 2. Queue Congestion / Wait
            elif "queue" in comp or op in ("wait", "queue_wait", "celery_enqueue", "outbox_poll"):
                if dur >= self.config.slow_queue_threshold_ms or (pct >= ratio_threshold * 100 and dur >= 50.0):
                    severity = SeverityLevel.HIGH if dur >= self.config.slow_queue_threshold_ms * 2 else SeverityLevel.MEDIUM
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.QUEUE_CONGESTION,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=severity,
                            impact_summary=f"Queue wait time of {dur:.1f}ms ({pct:.1f}% of trace) indicates broker congestion.",
                            evidence={"span_id": span.span_id, "threshold_ms": self.config.slow_queue_threshold_ms},
                        )
                    )

            # 3. Slow Dispatcher
            elif comp == "dispatcher" or "dispatch" in op:
                if dur >= self.config.slow_dispatcher_threshold_ms:
                    severity = SeverityLevel.HIGH if dur >= self.config.slow_dispatcher_threshold_ms * 2 else SeverityLevel.MEDIUM
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.SLOW_DISPATCHER,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=severity,
                            impact_summary=f"Dispatcher cycle took {dur:.1f}ms ({pct:.1f}% of trace).",
                            evidence={"span_id": span.span_id, "threshold_ms": self.config.slow_dispatcher_threshold_ms},
                        )
                    )

            # 4. Worker Saturation / Wait
            elif "worker" in comp and op in ("execute", "worker_execute", "worker_dequeue"):
                if dur >= self.config.slow_worker_threshold_ms:
                    severity = SeverityLevel.HIGH if dur >= self.config.slow_worker_threshold_ms * 2 else SeverityLevel.MEDIUM
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.WORKER_SATURATION,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=severity,
                            impact_summary=f"Worker execution stage took {dur:.1f}ms ({pct:.1f}% of trace).",
                            evidence={"span_id": span.span_id, "threshold_ms": self.config.slow_worker_threshold_ms},
                        )
                    )

            # 5. Database Latency
            elif comp in ("event_store", "store") or "persist" in op or "db" in op:
                if dur >= self.config.slow_database_threshold_ms:
                    severity = SeverityLevel.HIGH if dur >= self.config.slow_database_threshold_ms * 2 else SeverityLevel.MEDIUM
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.DATABASE_LATENCY,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=severity,
                            impact_summary=f"Database operation {span.operation} took {dur:.1f}ms ({pct:.1f}% of trace).",
                            evidence={"span_id": span.span_id, "threshold_ms": self.config.slow_database_threshold_ms},
                        )
                    )

            # 6. Partition Lock Contention
            elif comp == "partition_scheduler" or "lock" in op or "partition" in op:
                if dur >= 50.0 or "conflict" in str(span.metadata).lower():
                    bottlenecks.append(
                        BottleneckReport(
                            trace_id=snapshot.trace_id,
                            category=BottleneckCategory.PARTITION_CONTENTION,
                            component=span.component,
                            operation=span.operation,
                            duration_ms=dur,
                            percentage_of_trace=pct,
                            severity=SeverityLevel.MEDIUM,
                            impact_summary=f"Partition lock acquisition latency of {dur:.1f}ms indicates partition contention.",
                            evidence={"span_id": span.span_id, "metadata": span.metadata},
                        )
                    )

        return bottlenecks
