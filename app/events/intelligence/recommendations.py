"""
HunterOS Engage — Recommendation Engine
app/events/intelligence/recommendations.py

Generates deterministic, evidence-based operational recommendations
from identified root causes, execution bottlenecks, and recurring patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    BottleneckCategory,
    BottleneckReport,
    FailureCategory,
    PatternReport,
    PatternType,
    Recommendation,
    RootCauseReport,
    SeverityLevel,
)


class AbstractRecommendationEngine(ABC):
    """
    Interface for operational recommendation engines.
    """

    @abstractmethod
    def generate_recommendations(
        self,
        root_causes: List[RootCauseReport],
        bottlenecks: List[BottleneckReport],
        patterns: List[PatternReport],
    ) -> List[Recommendation]:
        """
        Generates prioritized, actionable recommendations based on intelligence findings.
        """
        pass


class DefaultRecommendationEngine(AbstractRecommendationEngine):
    """
    Standard production recommendation engine.
    Produces deterministic advice backed by specific metric thresholds and span evidence.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def generate_recommendations(
        self,
        root_causes: List[RootCauseReport],
        bottlenecks: List[BottleneckReport],
        patterns: List[PatternReport],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        seen_keys = set()

        # 1. Recommendations from Bottlenecks
        for bn in bottlenecks:
            key = f"{bn.category.value}:{bn.component}"
            if key in seen_keys:
                continue

            if bn.category == BottleneckCategory.SLOW_CONSUMER:
                recommendations.append(
                    Recommendation(
                        title=f"Optimize Slow Consumer: {bn.component}",
                        description=f"Consumer {bn.component} took {bn.duration_ms:.1f}ms ({bn.percentage_of_trace:.1f}% of trace). Consider adding Redis caching, optimizing DB queries, or making heavy processing asynchronous.",
                        action_type="OPTIMIZE_CONSUMER",
                        target_component=bn.component,
                        priority=bn.severity,
                        evidence={"bottleneck_id": bn.bottleneck_id, "duration_ms": bn.duration_ms},
                    )
                )
                seen_keys.add(key)

            elif bn.category in (BottleneckCategory.QUEUE_CONGESTION, BottleneckCategory.WORKER_SATURATION):
                recommendations.append(
                    Recommendation(
                        title="Increase Celery Worker Concurrency",
                        description=f"Queue congestion / worker saturation of {bn.duration_ms:.1f}ms detected in {bn.component}. Scale worker pool replicas or increase worker concurrency settings.",
                        action_type="SCALE_WORKERS",
                        target_component=bn.component,
                        priority=SeverityLevel.HIGH,
                        evidence={"bottleneck_id": bn.bottleneck_id, "duration_ms": bn.duration_ms},
                    )
                )
                seen_keys.add(key)

            elif bn.category == BottleneckCategory.DATABASE_LATENCY:
                recommendations.append(
                    Recommendation(
                        title="Investigate Event Store Database Latency",
                        description=f"Database operations in {bn.component} took {bn.duration_ms:.1f}ms. Review PostgreSQL indexes on event_store, check connection pool size, or optimize disk IOPS.",
                        action_type="OPTIMIZE_DATABASE",
                        target_component=bn.component,
                        priority=bn.severity,
                        evidence={"bottleneck_id": bn.bottleneck_id, "duration_ms": bn.duration_ms},
                    )
                )
                seen_keys.add(key)

            elif bn.category == BottleneckCategory.PARTITION_CONTENTION:
                recommendations.append(
                    Recommendation(
                        title="Mitigate Partition Lock Contention",
                        description=f"Partition lock acquisition delay of {bn.duration_ms:.1f}ms in {bn.component}. Review partition key distribution and reduce lock hold duration.",
                        action_type="REPARTITION",
                        target_component=bn.component,
                        priority=SeverityLevel.MEDIUM,
                        evidence={"bottleneck_id": bn.bottleneck_id, "duration_ms": bn.duration_ms},
                    )
                )
                seen_keys.add(key)

        # 2. Recommendations from Recurring Patterns
        for pt in patterns:
            key = f"{pt.pattern_type.value}:{':'.join(pt.affected_entities)}"
            if key in seen_keys:
                continue

            if pt.pattern_type == PatternType.PARTITION_HOTSPOT:
                recommendations.append(
                    Recommendation(
                        title=f"Partition Hotspot Detected: {pt.affected_entities[0]}",
                        description=f"Partition '{pt.affected_entities[0]}' handles a disproportionate share of events ({pt.occurrences} occurrences). Introduce hierarchical composite partition keys to distribute load.",
                        action_type="REPARTITION",
                        target_component=f"partition:{pt.affected_entities[0]}",
                        priority=pt.severity,
                        evidence=pt.evidence,
                    )
                )
                seen_keys.add(key)

            elif pt.pattern_type == PatternType.RETRY_STORM:
                recommendations.append(
                    Recommendation(
                        title="Mitigate Retry Storm",
                        description=f"Detected {pt.occurrences} retries in recent history. Enable circuit breaker backpressure or increase initial retry backoff intervals to protect downstream dependencies.",
                        action_type="CONFIGURE_BACKOFF",
                        target_component="retry_engine",
                        priority=SeverityLevel.CRITICAL,
                        evidence=pt.evidence,
                    )
                )
                seen_keys.add(key)

            elif pt.pattern_type == PatternType.REPEATED_FAILURE:
                target = pt.affected_entities[0] if pt.affected_entities else "unknown"
                recommendations.append(
                    Recommendation(
                        title=f"Investigate Recurring Failure: {target}",
                        description=f"Repeated failures ({pt.occurrences} times) detected on '{target}'. Review error traces and add guardrail validation.",
                        action_type="FIX_BUGS",
                        target_component=target,
                        priority=SeverityLevel.HIGH,
                        evidence=pt.evidence,
                    )
                )
                seen_keys.add(key)

        # 3. Recommendations from Root Causes
        for rc in root_causes:
            key = f"{rc.category.value}:{rc.originating_component}"
            if key in seen_keys:
                continue

            if rc.category == FailureCategory.SCHEMA_MISMATCH:
                recommendations.append(
                    Recommendation(
                        title=f"Schema Validation Mismatch in {rc.originating_component}",
                        description=f"Schema mismatch detected: {rc.error_message}. Register a schema version upgrade adapter in SchemaRegistry.",
                        action_type="REGISTER_SCHEMA_ADAPTER",
                        target_component=rc.originating_component,
                        priority=SeverityLevel.HIGH,
                        evidence={"trace_id": rc.trace_id, "error": rc.error_message},
                    )
                )
                seen_keys.add(key)

        # Limit total recommendations
        return recommendations[: self.config.max_recommendations]
