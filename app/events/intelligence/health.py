"""
HunterOS Engage — Health Calculator
app/events/intelligence/health.py

Calculates multi-dimensional subsystem health scores (0-100) and overall platform health
based on completed traces, failures, bottlenecks, patterns, and latency.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    BottleneckCategory,
    BottleneckReport,
    ComponentHealth,
    HealthComponent,
    PatternReport,
    PatternType,
    RootCauseReport,
    SystemHealthReport,
)
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import SpanStatus


class AbstractHealthCalculator(ABC):
    """
    Interface for platform execution health calculators.
    """

    @abstractmethod
    def calculate_health(
        self,
        snapshots: List[TraceSnapshot],
        root_causes: List[RootCauseReport],
        bottlenecks: List[BottleneckReport],
        patterns: List[PatternReport],
    ) -> SystemHealthReport:
        """
        Computes multi-dimensional health metrics across all event platform subsystems.
        """
        pass


class DefaultHealthCalculator(AbstractHealthCalculator):
    """
    Standard multi-dimensional health calculator.
    Provides deterministic scoring from 0 to 100 with actionable penalty justifications.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def calculate_health(
        self,
        snapshots: List[TraceSnapshot],
        root_causes: List[RootCauseReport],
        bottlenecks: List[BottleneckReport],
        patterns: List[PatternReport],
    ) -> SystemHealthReport:
        total_traces = len(snapshots)

        if total_traces == 0:
            # Clean baseline if no completed traces yet
            return self._baseline_health()

        failed_traces = [s for s in snapshots if s.root_span and s.root_span.status == SpanStatus.FAILED]
        failure_rate = len(failed_traces) / total_traces

        # 1. Dispatcher Health
        disp_score = 100
        disp_reasons = []
        disp_bottlenecks = [b for b in bottlenecks if b.category == BottleneckCategory.SLOW_DISPATCHER]
        if disp_bottlenecks:
            penalty = min(40, len(disp_bottlenecks) * 15)
            disp_score -= penalty
            disp_reasons.append(f"{len(disp_bottlenecks)} slow dispatcher operations detected (-{penalty})")

        # 2. Worker Health
        worker_score = 100
        worker_reasons = []
        worker_bottlenecks = [b for b in bottlenecks if b.category == BottleneckCategory.WORKER_SATURATION]
        if worker_bottlenecks:
            penalty = min(40, len(worker_bottlenecks) * 15)
            worker_score -= penalty
            worker_reasons.append(f"{len(worker_bottlenecks)} worker saturation events (-{penalty})")
        worker_hotspots = [p for p in patterns if p.pattern_type == PatternType.WORKER_HOTSPOT]
        if worker_hotspots:
            worker_score -= 15
            worker_reasons.append("Worker execution skew detected (-15)")

        # 3. Consumer Health
        consumer_score = 100
        consumer_reasons = []
        slow_consumers = [b for b in bottlenecks if b.category == BottleneckCategory.SLOW_CONSUMER]
        if slow_consumers:
            penalty = min(35, len(slow_consumers) * 10)
            consumer_score -= penalty
            consumer_reasons.append(f"{len(slow_consumers)} slow consumer executions (-{penalty})")
        consumer_failures = [rc for rc in root_causes if "consumer" in rc.originating_component.lower()]
        if consumer_failures:
            penalty = min(40, len(consumer_failures) * 15)
            consumer_score -= penalty
            consumer_reasons.append(f"{len(consumer_failures)} consumer execution exceptions (-{penalty})")

        # 4. Partition Health
        partition_score = 100
        partition_reasons = []
        partition_hotspots = [p for p in patterns if p.pattern_type == PatternType.PARTITION_HOTSPOT]
        if partition_hotspots:
            partition_score -= 25
            partition_reasons.append(f"{len(partition_hotspots)} partition hotspot(s) detected (-25)")
        partition_contentions = [b for b in bottlenecks if b.category == BottleneckCategory.PARTITION_CONTENTION]
        if partition_contentions:
            penalty = min(30, len(partition_contentions) * 15)
            partition_score -= penalty
            partition_reasons.append(f"{len(partition_contentions)} partition lock contention events (-{penalty})")

        # 5. Retry Health
        retry_score = 100
        retry_reasons = []
        retry_storms = [p for p in patterns if p.pattern_type == PatternType.RETRY_STORM]
        if retry_storms:
            retry_score -= 40
            retry_reasons.append("Active retry storm detected (-40)")
        total_retries = sum(len(s.retry_history) for s in snapshots)
        if total_retries > 0:
            penalty = min(30, total_retries * 5)
            retry_score -= penalty
            retry_reasons.append(f"{total_retries} retries recorded in window (-{penalty})")

        # 6. Latency Health
        latency_score = 100
        latency_reasons = []
        durations = [s.root_span.duration_ms for s in snapshots if s.root_span and s.root_span.duration_ms is not None]
        if durations:
            avg_dur = sum(durations) / len(durations)
            if avg_dur > 200.0:
                penalty = min(40, int((avg_dur - 200.0) / 10))
                latency_score -= penalty
                latency_reasons.append(f"Average execution latency {avg_dur:.1f}ms exceeds target (-{penalty})")

        # 7. Failure Health
        failure_score = max(0, int(100 - (failure_rate * 100)))
        failure_reasons = []
        if failure_rate > 0:
            failure_reasons.append(f"Failure rate is {failure_rate * 100:.1f}% ({len(failed_traces)}/{total_traces} failed)")

        # Clamp all scores between 0 and 100
        disp_score = max(0, min(100, disp_score))
        worker_score = max(0, min(100, worker_score))
        consumer_score = max(0, min(100, consumer_score))
        partition_score = max(0, min(100, partition_score))
        retry_score = max(0, min(100, retry_score))
        latency_score = max(0, min(100, latency_score))
        failure_score = max(0, min(100, failure_score))

        # Overall Score (Weighted Average)
        weights = {
            "failure": 0.30,
            "consumer": 0.20,
            "latency": 0.15,
            "worker": 0.10,
            "dispatcher": 0.10,
            "partition": 0.10,
            "retry": 0.05,
        }
        overall_score = int(
            failure_score * weights["failure"]
            + consumer_score * weights["consumer"]
            + latency_score * weights["latency"]
            + worker_score * weights["worker"]
            + disp_score * weights["dispatcher"]
            + partition_score * weights["partition"]
            + retry_score * weights["retry"]
        )
        if failure_rate > 0.3:
            overall_score = int(overall_score * (1.0 - (failure_rate * 0.5)))
        overall_score = max(0, min(100, overall_score))

        subsystems: Dict[str, ComponentHealth] = {
            HealthComponent.DISPATCHER.value: ComponentHealth(
                component=HealthComponent.DISPATCHER,
                score=disp_score,
                status=self._status_for_score(disp_score),
                reasons=disp_reasons or ["Dispatcher functioning normally."],
            ),
            HealthComponent.WORKER.value: ComponentHealth(
                component=HealthComponent.WORKER,
                score=worker_score,
                status=self._status_for_score(worker_score),
                reasons=worker_reasons or ["Worker execution healthy."],
            ),
            HealthComponent.CONSUMER.value: ComponentHealth(
                component=HealthComponent.CONSUMER,
                score=consumer_score,
                status=self._status_for_score(consumer_score),
                reasons=consumer_reasons or ["Consumer execution healthy."],
            ),
            HealthComponent.PARTITION.value: ComponentHealth(
                component=HealthComponent.PARTITION,
                score=partition_score,
                status=self._status_for_score(partition_score),
                reasons=partition_reasons or ["Partition distribution balanced."],
            ),
            HealthComponent.RETRY.value: ComponentHealth(
                component=HealthComponent.RETRY,
                score=retry_score,
                status=self._status_for_score(retry_score),
                reasons=retry_reasons or ["No retry anomalies."],
            ),
            HealthComponent.LATENCY.value: ComponentHealth(
                component=HealthComponent.LATENCY,
                score=latency_score,
                status=self._status_for_score(latency_score),
                reasons=latency_reasons or ["Latency within acceptable bounds."],
            ),
            HealthComponent.FAILURE.value: ComponentHealth(
                component=HealthComponent.FAILURE,
                score=failure_score,
                status=self._status_for_score(failure_score),
                reasons=failure_reasons or ["Zero failures detected."],
            ),
        }

        return SystemHealthReport(
            overall_score=overall_score,
            status=self._status_for_score(overall_score),
            subsystem_health=subsystems,
            active_bottlenecks_count=len(bottlenecks),
            active_failures_count=len(root_causes),
            active_patterns_count=len(patterns),
        )

    def _status_for_score(self, score: int) -> str:
        if score >= 80:
            return "HEALTHY"
        elif score >= 50:
            return "DEGRADED"
        return "CRITICAL"

    def _baseline_health(self) -> SystemHealthReport:
        subsystems = {
            c.value: ComponentHealth(component=c, score=100, status="HEALTHY", reasons=["Baseline state."])
            for c in HealthComponent
            if c != HealthComponent.OVERALL
        }
        return SystemHealthReport(
            overall_score=100,
            status="HEALTHY",
            subsystem_health=subsystems,
            active_bottlenecks_count=0,
            active_failures_count=0,
            active_patterns_count=0,
        )
