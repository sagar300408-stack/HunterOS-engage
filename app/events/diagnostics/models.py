"""
HunterOS Engage — Runtime Diagnostics Models
app/events/diagnostics/models.py

Domain models and schemas for live runtime inspection, subsystem diagnostics,
and consistent observation snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class SubsystemType(str, Enum):
    WORKERS = "WORKERS"
    DISPATCHERS = "DISPATCHERS"
    QUEUES = "QUEUES"
    PARTITIONS = "PARTITIONS"
    LOCKS = "LOCKS"
    CONSUMERS = "CONSUMERS"
    SCHEDULER = "SCHEDULER"
    HEALTH = "HEALTH"


class RuntimeHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


# ── Base Model with Consistent Observation Point ─────────────────────────────

class BaseDiagnosticsReport(BaseModel):
    """
    Base class stamping every diagnostic section with the exact logical
    observation point (snapshot_id and snapshot_timestamp) to guarantee
    cross-collector consistency.
    """
    snapshot_id: str = Field(..., description="Unique identifier of the logical observation window")
    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Immutable UTC timestamp when the snapshot began",
    )


# ── Worker Diagnostics Models ────────────────────────────────────────────────

class WorkerDetail(BaseModel):
    worker_id: str
    status: str = "IDLE"  # ACTIVE, IDLE, BUSY, TERMINATED
    current_task_id: Optional[str] = None
    current_event_id: Optional[str] = None
    current_partition_key: Optional[str] = None
    execution_duration_ms: Optional[float] = None
    total_completed_tasks: int = 0
    total_failed_tasks: int = 0
    last_heartbeat: Optional[datetime] = None


class WorkerDiagnostics(BaseDiagnosticsReport):
    status: str = "HEALTHY"
    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    executing_events_count: int = 0
    worker_utilization_pct: float = 0.0
    average_execution_duration_ms: float = 0.0
    worker_throughput_per_sec: float = 0.0
    worker_failures_count: int = 0
    workers: List[WorkerDetail] = Field(default_factory=list)


# ── Dispatcher Diagnostics Models ────────────────────────────────────────────

class DispatcherDetail(BaseModel):
    dispatcher_id: str
    is_leader: bool = False
    cluster_epoch: int = 1
    poll_frequency_sec: float = 1.0
    last_poll_at: Optional[datetime] = None
    assigned_partitions_count: int = 0
    dispatched_events_total: int = 0
    status: str = "HEALTHY"


class DispatcherDiagnostics(BaseDiagnosticsReport):
    active_dispatchers_count: int = 0
    leader_dispatcher_id: Optional[str] = None
    cluster_epoch: int = 1
    average_poll_frequency_sec: float = 0.0
    dispatch_latency_ms: float = 0.0
    dispatcher_ownership: Dict[str, int] = Field(default_factory=dict)
    outbox_queue_depth: int = 0
    scheduling_latency_ms: float = 0.0
    dispatchers: List[DispatcherDetail] = Field(default_factory=list)


# ── Queue Diagnostics Models ─────────────────────────────────────────────────

class QueueBreakdown(BaseModel):
    pending: int = 0
    queued: int = 0
    processing: int = 0
    retrying: int = 0
    dead_letter: int = 0
    replayed: int = 0


class QueueDiagnostics(BaseDiagnosticsReport):
    total_depth: int = 0
    breakdown: QueueBreakdown = Field(default_factory=QueueBreakdown)
    average_wait_time_ms: float = 0.0
    throughput_per_sec: float = 0.0
    dead_letter_rate: float = 0.0
    retry_rate: float = 0.0


# ── Partition Diagnostics Models ─────────────────────────────────────────────

class PartitionDetail(BaseModel):
    partition_key: str
    state: str = "ACTIVE"  # ACTIVE, WAITING, IDLE, LOCKED
    pending_events_count: int = 0
    oldest_event_age_sec: Optional[float] = None
    lock_owner: Optional[str] = None
    lock_remaining_seconds: Optional[float] = None


class PartitionDiagnostics(BaseDiagnosticsReport):
    total_partitions: int = 0
    active_partitions_count: int = 0
    waiting_partitions_count: int = 0
    total_partition_backlog: int = 0
    hottest_partitions: List[PartitionDetail] = Field(default_factory=list)
    oldest_event_age_sec: float = 0.0
    partition_throughput_per_sec: float = 0.0
    partitions: List[PartitionDetail] = Field(default_factory=list)


# ── Lock Diagnostics Models ──────────────────────────────────────────────────

class LockDetail(BaseModel):
    resource_id: str
    owner_id: str
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remaining_lease_sec: float = 0.0
    is_expired: bool = False


class LockDiagnostics(BaseDiagnosticsReport):
    active_locks_count: int = 0
    expired_locks_count: int = 0
    lock_owners: Dict[str, int] = Field(default_factory=dict)
    average_lease_duration_sec: float = 0.0
    lock_contention_events_total: int = 0
    locks: List[LockDetail] = Field(default_factory=list)


# ── Consumer Diagnostics Models ──────────────────────────────────────────────

class ConsumerDetail(BaseModel):
    consumer_name: str
    event_types: List[str] = Field(default_factory=list)
    execution_count: int = 0
    failure_count: int = 0
    failure_rate: float = 0.0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    dependencies: List[str] = Field(default_factory=list)


class ConsumerDiagnostics(BaseDiagnosticsReport):
    total_consumers_registered: int = 0
    total_executions: int = 0
    total_failures: int = 0
    overall_average_latency_ms: float = 0.0
    slowest_consumers: List[ConsumerDetail] = Field(default_factory=list)
    consumer_dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    consumers: List[ConsumerDetail] = Field(default_factory=list)


# ── Scheduler Diagnostics Models ─────────────────────────────────────────────

class SchedulerDetail(BaseModel):
    scheduler_policy: str = "DeficitRoundRobin"
    active_queues: int = 0
    scheduling_cycles_total: int = 0
    average_plan_generation_ms: float = 0.0
    deficit_counters: Dict[str, int] = Field(default_factory=dict)


class SchedulerDiagnostics(BaseDiagnosticsReport):
    scheduler_policy: str = "DeficitRoundRobin"
    total_scheduling_cycles: int = 0
    fairness_deficit_balance: Dict[str, int] = Field(default_factory=dict)
    priority_flow_rates: Dict[str, float] = Field(default_factory=dict)
    average_scheduling_latency_ms: float = 0.0
    scheduler_details: SchedulerDetail = Field(default_factory=SchedulerDetail)


# ── Health & Early Warning Models ────────────────────────────────────────────

class EarlyWarningIndicator(BaseModel):
    warning_id: str
    subsystem: SubsystemType
    severity: str = "WARNING"  # WARNING, CRITICAL
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    recommended_action: str


class SubsystemHealthStatus(BaseModel):
    subsystem: SubsystemType
    score: int = 100
    status: RuntimeHealthStatus = RuntimeHealthStatus.HEALTHY
    reasons: List[str] = Field(default_factory=list)


class RuntimeHealthSummary(BaseDiagnosticsReport):
    overall_score: int = 100
    overall_status: RuntimeHealthStatus = RuntimeHealthStatus.HEALTHY
    subsystem_health: Dict[str, SubsystemHealthStatus] = Field(default_factory=dict)
    resource_utilization: Dict[str, float] = Field(default_factory=dict)
    capacity_estimation: Dict[str, Any] = Field(default_factory=dict)
    early_warning_indicators: List[EarlyWarningIndicator] = Field(default_factory=list)


# ── Comprehensive Unified Runtime Snapshot ───────────────────────────────────

class RuntimeSnapshot(BaseModel):
    """
    Consistent point-in-time snapshot representing all subsystems at a single
    logical observation point.
    """
    snapshot_id: str
    snapshot_timestamp: datetime
    observation_window_ms: float = 0.0
    workers: WorkerDiagnostics
    dispatchers: DispatcherDiagnostics
    queues: QueueDiagnostics
    partitions: PartitionDiagnostics
    locks: LockDiagnostics
    consumers: ConsumerDiagnostics
    scheduler: SchedulerDiagnostics
    health: RuntimeHealthSummary


# ── Live Inspection Query & Result ───────────────────────────────────────────

class LiveInspectionQuery(BaseModel):
    subsystem: SubsystemType
    entity_id: Optional[str] = None
    filter_state: Optional[str] = None
    limit: int = 50


class LiveInspectionResult(BaseDiagnosticsReport):
    subsystem: SubsystemType
    matched_count: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)
