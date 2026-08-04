"""
HunterOS Engage — Execution Intelligence Data Models
app/events/intelligence/models.py

Domain models and enums for root cause analysis, bottleneck detection,
pattern recognition, health scoring, and actionable recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class FailureCategory(str, Enum):
    CONSUMER_EXCEPTION = "CONSUMER_EXCEPTION"
    TIMEOUT = "TIMEOUT"
    LOCK_CONTENTION = "LOCK_CONTENTION"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    DATABASE_ERROR = "DATABASE_ERROR"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    QUEUE_CONGESTION = "QUEUE_CONGESTION"
    SYSTEM_PANIC = "SYSTEM_PANIC"
    UNKNOWN = "UNKNOWN"


class BottleneckCategory(str, Enum):
    SLOW_CONSUMER = "SLOW_CONSUMER"
    SLOW_DISPATCHER = "SLOW_DISPATCHER"
    QUEUE_CONGESTION = "QUEUE_CONGESTION"
    WORKER_SATURATION = "WORKER_SATURATION"
    PARTITION_CONTENTION = "PARTITION_CONTENTION"
    DATABASE_LATENCY = "DATABASE_LATENCY"
    RETRY_STORM = "RETRY_STORM"
    CLUSTER_IMBALANCE = "CLUSTER_IMBALANCE"


class SeverityLevel(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HealthComponent(str, Enum):
    OVERALL = "OVERALL"
    DISPATCHER = "DISPATCHER"
    WORKER = "WORKER"
    CONSUMER = "CONSUMER"
    PARTITION = "PARTITION"
    CLUSTER = "CLUSTER"
    RETRY = "RETRY"
    LATENCY = "LATENCY"
    FAILURE = "FAILURE"


class PatternType(str, Enum):
    REPEATED_FAILURE = "REPEATED_FAILURE"
    RECURRING_SLOW_CONSUMER = "RECURRING_SLOW_CONSUMER"
    PARTITION_HOTSPOT = "PARTITION_HOTSPOT"
    WORKER_HOTSPOT = "WORKER_HOTSPOT"
    DISPATCHER_HOTSPOT = "DISPATCHER_HOTSPOT"
    RETRY_STORM = "RETRY_STORM"
    DEAD_LETTER_HOTSPOT = "DEAD_LETTER_HOTSPOT"


@dataclass
class RootCauseReport:
    """
    Detailed root cause analysis report for a failed trace execution.
    """
    trace_id: str
    category: FailureCategory
    originating_component: str
    originating_operation: str
    error_message: str
    error_type: Optional[str] = None
    root_cause_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_id: Optional[str] = None
    workspace_id: Optional[str] = None
    primary_failure: Dict[str, Any] = field(default_factory=dict)
    failure_chain: List[Dict[str, Any]] = field(default_factory=list)
    downstream_impacted_components: List[str] = field(default_factory=list)
    is_retry_failure: bool = False
    is_replay_failure: bool = False
    recommendation_summary: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.HIGH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause_id": self.root_cause_id,
            "trace_id": self.trace_id,
            "event_id": self.event_id,
            "workspace_id": self.workspace_id,
            "category": self.category.value if isinstance(self.category, Enum) else str(self.category),
            "originating_component": self.originating_component,
            "originating_operation": self.originating_operation,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "primary_failure": self.primary_failure,
            "failure_chain": self.failure_chain,
            "downstream_impacted_components": self.downstream_impacted_components,
            "is_retry_failure": self.is_retry_failure,
            "is_replay_failure": self.is_replay_failure,
            "recommendation_summary": self.recommendation_summary,
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BottleneckReport:
    """
    Identified execution bottleneck within a trace or aggregate history.
    """
    category: BottleneckCategory
    component: str
    operation: str
    duration_ms: float
    percentage_of_trace: float
    impact_summary: str
    bottleneck_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bottleneck_id": self.bottleneck_id,
            "trace_id": self.trace_id,
            "category": self.category.value if isinstance(self.category, Enum) else str(self.category),
            "component": self.component,
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 3),
            "percentage_of_trace": round(self.percentage_of_trace, 2),
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "impact_summary": self.impact_summary,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PatternReport:
    """
    Detected recurring execution pattern or system hotspot across multiple traces.
    """
    pattern_type: PatternType
    description: str
    occurrences: int
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    affected_entities: List[str] = field(default_factory=list)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value if isinstance(self.pattern_type, Enum) else str(self.pattern_type),
            "description": self.description,
            "occurrences": self.occurrences,
            "affected_entities": self.affected_entities,
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "evidence": self.evidence,
        }


@dataclass
class AnomalyReport:
    """
    Statistical anomaly detected during trace execution.
    """
    metric_name: str
    observed_value: float
    expected_value: float
    z_score: float
    description: str
    anomaly_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.LOW
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "trace_id": self.trace_id,
            "metric_name": self.metric_name,
            "observed_value": round(self.observed_value, 3),
            "expected_value": round(self.expected_value, 3),
            "z_score": round(self.z_score, 2),
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Recommendation:
    """
    Deterministic, evidence-based operational recommendation.
    """
    title: str
    description: str
    action_type: str
    target_component: str
    recommendation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    priority: SeverityLevel = SeverityLevel.MEDIUM
    evidence: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "target_component": self.target_component,
            "priority": self.priority.value if isinstance(self.priority, Enum) else str(self.priority),
            "evidence": self.evidence,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ComponentHealth:
    """
    Health breakdown for a specific subsystem.
    """
    component: HealthComponent
    score: int  # 0 to 100
    status: str  # HEALTHY, DEGRADED, CRITICAL
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component.value if isinstance(self.component, Enum) else str(self.component),
            "score": self.score,
            "status": self.status,
            "reasons": self.reasons,
        }


@dataclass
class SystemHealthReport:
    """
    Comprehensive multi-dimensional health assessment of the event processing platform.
    """
    overall_score: int  # 0 to 100
    status: str  # HEALTHY, DEGRADED, CRITICAL
    subsystem_health: Dict[str, ComponentHealth] = field(default_factory=dict)
    active_bottlenecks_count: int = 0
    active_failures_count: int = 0
    active_patterns_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "status": self.status,
            "subsystem_health": {k: v.to_dict() for k, v in self.subsystem_health.items()},
            "active_bottlenecks_count": self.active_bottlenecks_count,
            "active_failures_count": self.active_failures_count,
            "active_patterns_count": self.active_patterns_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionIntelligenceReport:
    """
    Unified intelligence report combining health, root causes, bottlenecks,
    patterns, anomalies, recommendations, and execution statistics.
    """
    health: SystemHealthReport
    root_causes: List[RootCauseReport] = field(default_factory=list)
    bottlenecks: List[BottleneckReport] = field(default_factory=list)
    patterns: List[PatternReport] = field(default_factory=list)
    anomalies: List[AnomalyReport] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    total_traces_analyzed: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health": self.health.to_dict(),
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "bottlenecks": [bn.to_dict() for bn in self.bottlenecks],
            "patterns": [pt.to_dict() for pt in self.patterns],
            "anomalies": [an.to_dict() for an in self.anomalies],
            "recommendations": [rc.to_dict() for rc in self.recommendations],
            "total_traces_analyzed": self.total_traces_analyzed,
            "timestamp": self.timestamp.isoformat(),
        }
