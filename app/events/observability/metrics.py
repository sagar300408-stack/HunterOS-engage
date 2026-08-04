"""
HunterOS Engage — Event Pipeline Metrics
app/events/observability/metrics.py

Thread-safe, process-local counters for every significant pipeline event.
For a single-worker deployment this provides sub-millisecond overhead.
For multi-worker deployments, replace the backing store with Redis INCR
commands while keeping the same public interface.

Counters
────────
    processed                         — events successfully COMPLETED.
    failed                            — events that transitioned to FAILED or DEAD_LETTER.
    retried                           — retry transitions recorded.
    dead_lettered                     — events moved to DEAD_LETTER.
    replayed                          — events re-queued via the replay API.
    active_processing                 — gauge: events currently in PROCESSING state.
    dispatcher_cycles                 — total dispatch() invocations (Celery task activations).
    idempotency_keys_generated        — total deterministic idempotency keys generated.
    duplicate_events_blocked          — duplicate event publications successfully suppressed.
    replay_bypasses                   — replay operations that intentionally bypassed duplicate check.
    uniqueness_conflicts              — concurrent insert race conditions caught by unique DB constraint.
    idempotency_lookups               — pre-persist idempotency DB lookups performed.
    idempotency_lookup_duration_ms_tot— cumulative duration in milliseconds for idempotency lookups.
    active_partitions                 — gauge: distinct non-locked partitions with pending events.
    waiting_partitions                — gauge: partitions blocked by active locks.
    largest_partition                 — gauge: event count of the largest pending partition.
    partition_locks_acquired          — total partition lock leases acquired.
    partition_locks_released          — total partition lock leases released.
    partition_lock_conflicts          — partition lock acquisition rejections due to active hold.
    partition_lock_timeouts           — partition locks auto-reclaimed due to TTL expiration.
    scheduler_cycles                  — total execution planning cycles run by partition scheduler.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict


# ── Snapshot (immutable, safe to pass across threads) ─────────────────────────

@dataclass(frozen=True)
class MetricsSnapshot:
    """
    Point-in-time copy of all pipeline counters.

    All values are non-negative integers.  Gauges (active_processing) reflect
    the current estimate; counters (processed, failed, …) are monotonically
    increasing totals since process startup.
    """
    events_processed:                  int
    events_failed:                     int
    events_retried:                    int
    events_dead_lettered:              int
    events_replayed:                   int
    events_active_processing:          int
    dispatcher_cycles:                 int
    idempotency_keys_generated:        int = 0
    duplicate_events_blocked:          int = 0
    replay_bypasses:                   int = 0
    uniqueness_conflicts:              int = 0
    idempotency_lookups:               int = 0
    idempotency_lookup_duration_ms_tot: int = 0
    # Partition Observability Metrics
    active_partitions:                 int = 0
    waiting_partitions:                int = 0
    largest_partition:                 int = 0
    partition_locks_acquired:          int = 0
    partition_locks_released:          int = 0
    partition_lock_conflicts:          int = 0
    partition_lock_timeouts:           int = 0
    scheduler_cycles:                  int = 0
    # Priority & Backpressure Metrics
    priority_critical_dispatched:      int = 0
    priority_high_dispatched:          int = 0
    priority_normal_dispatched:        int = 0
    priority_low_dispatched:           int = 0
    priority_background_dispatched:    int = 0
    priority_aging_promotions:         int = 0
    dispatcher_backpressure_events:    int = 0
    dispatcher_throttled_events:       int = 0
    dispatcher_queue_depth:            int = 0
    queue_health_score:                int = 100
    worker_utilization:                int = 0
    # Cluster Coordination & Leadership Metrics
    cluster_epoch:                     int = 1
    current_ring_version:              int = 0
    membership_changes:                int = 0
    cluster_nodes:                     int = 0
    healthy_nodes:                     int = 0
    leader_changes:                    int = 0
    dispatcher_heartbeats:             int = 0
    dispatcher_failures:               int = 0
    leadership_acquisitions:           int = 0
    leadership_losses:                 int = 0
    dispatcher_assignments:            int = 0
    dispatcher_load:                   int = 0
    cluster_health_score:              int = 100
    cluster_uptime:                    int = 0
    # Distributed Tracing Metrics
    active_traces:                     int = 0
    completed_traces:                  int = 0
    failed_traces:                     int = 0
    span_count:                        int = 0
    average_trace_duration:            int = 0
    average_spans_per_trace:           int = 0
    trace_storage_size:                int = 0
    critical_path_duration:            int = 0
    slowest_trace:                     int = 0
    slowest_component:                 int = 0
    trace_search_requests:             int = 0
    trace_retention_cleanup:           int = 0
    # Execution Intelligence Metrics
    execution_health_score:            int = 100
    root_causes_detected:              int = 0
    bottlenecks_detected:              int = 0
    recommendations_generated:         int = 0
    retry_patterns:                    int = 0
    failure_patterns:                  int = 0
    latency_patterns:                  int = 0
    consumer_hotspots:                 int = 0
    partition_hotspots:                int = 0
    worker_hotspots:                   int = 0
    dispatcher_hotspots:               int = 0

    @property
    def duplicate_rate(self) -> float:
        """Percentage of incoming events suppressed as duplicates (0.0 to 1.0)."""
        total = self.idempotency_keys_generated + self.duplicate_events_blocked
        return (self.duplicate_events_blocked / total) if total > 0 else 0.0

    @property
    def avg_idempotency_lookup_latency_ms(self) -> float:
        """Average latency for idempotency store lookups in milliseconds."""
        return (
            (self.idempotency_lookup_duration_ms_tot / self.idempotency_lookups)
            if self.idempotency_lookups > 0
            else 0.0
        )

    def to_dict(self) -> dict:
        return {
            "events_processed":                  self.events_processed,
            "events_failed":                     self.events_failed,
            "events_retried":                    self.events_retried,
            "events_dead_lettered":              self.events_dead_lettered,
            "events_replayed":                   self.events_replayed,
            "events_active_processing":          self.events_active_processing,
            "dispatcher_cycles":                 self.dispatcher_cycles,
            "idempotency_keys_generated":        self.idempotency_keys_generated,
            "duplicate_events_blocked":          self.duplicate_events_blocked,
            "replay_bypasses":                   self.replay_bypasses,
            "uniqueness_conflicts":              self.uniqueness_conflicts,
            "idempotency_lookups":               self.idempotency_lookups,
            "duplicate_rate":                    round(self.duplicate_rate, 4),
            "avg_idempotency_lookup_latency_ms": round(self.avg_idempotency_lookup_latency_ms, 2),
            "active_partitions":                 self.active_partitions,
            "waiting_partitions":                self.waiting_partitions,
            "largest_partition":                 self.largest_partition,
            "partition_locks_acquired":          self.partition_locks_acquired,
            "partition_locks_released":          self.partition_locks_released,
            "partition_lock_conflicts":          self.partition_lock_conflicts,
            "partition_lock_timeouts":           self.partition_lock_timeouts,
            "scheduler_cycles":                  self.scheduler_cycles,
            "priority_critical_dispatched":      self.priority_critical_dispatched,
            "priority_high_dispatched":          self.priority_high_dispatched,
            "priority_normal_dispatched":        self.priority_normal_dispatched,
            "priority_low_dispatched":           self.priority_low_dispatched,
            "priority_background_dispatched":    self.priority_background_dispatched,
            "priority_aging_promotions":         self.priority_aging_promotions,
            "dispatcher_backpressure_events":    self.dispatcher_backpressure_events,
            "dispatcher_throttled_events":       self.dispatcher_throttled_events,
            "dispatcher_queue_depth":            self.dispatcher_queue_depth,
            "queue_health_score":                self.queue_health_score,
            "worker_utilization":                self.worker_utilization,
            "cluster_epoch":                     self.cluster_epoch,
            "current_ring_version":              self.current_ring_version,
            "membership_changes":                self.membership_changes,
            "cluster_nodes":                     self.cluster_nodes,
            "healthy_nodes":                     self.healthy_nodes,
            "leader_changes":                    self.leader_changes,
            "dispatcher_heartbeats":             self.dispatcher_heartbeats,
            "dispatcher_failures":               self.dispatcher_failures,
            "leadership_acquisitions":           self.leadership_acquisitions,
            "leadership_losses":                 self.leadership_losses,
            "dispatcher_assignments":            self.dispatcher_assignments,
            "dispatcher_load":                   self.dispatcher_load,
            "cluster_health_score":              self.cluster_health_score,
            "cluster_uptime":                    self.cluster_uptime,
            "active_traces":                     self.active_traces,
            "completed_traces":                  self.completed_traces,
            "failed_traces":                     self.failed_traces,
            "span_count":                        self.span_count,
            "average_trace_duration":            self.average_trace_duration,
            "average_spans_per_trace":           self.average_spans_per_trace,
            "trace_storage_size":                self.trace_storage_size,
            "critical_path_duration":            self.critical_path_duration,
            "slowest_trace":                     self.slowest_trace,
            "slowest_component":                 self.slowest_component,
            "trace_search_requests":             self.trace_search_requests,
            "trace_retention_cleanup":           self.trace_retention_cleanup,
            "execution_health_score":            self.execution_health_score,
            "root_causes_detected":              self.root_causes_detected,
            "bottlenecks_detected":              self.bottlenecks_detected,
            "recommendations_generated":         self.recommendations_generated,
            "retry_patterns":                    self.retry_patterns,
            "failure_patterns":                  self.failure_patterns,
            "latency_patterns":                  self.latency_patterns,
            "consumer_hotspots":                 self.consumer_hotspots,
            "partition_hotspots":                self.partition_hotspots,
            "worker_hotspots":                   self.worker_hotspots,
            "dispatcher_hotspots":               self.dispatcher_hotspots,
        }


# ── Metrics store ─────────────────────────────────────────────────────────────

_COUNTER_KEYS = (
    "processed",
    "failed",
    "retried",
    "dead_lettered",
    "replayed",
    "active_processing",
    "dispatcher_cycles",
    "idempotency_keys_generated",
    "generated_keys",
    "duplicate_events_blocked",
    "replay_bypasses",
    "uniqueness_conflicts",
    "idempotency_lookups",
    "idempotency_lookup_duration_ms_tot",
    "active_partitions",
    "waiting_partitions",
    "largest_partition",
    "partition_locks_acquired",
    "partition_locks_released",
    "partition_lock_conflicts",
    "partition_lock_timeouts",
    "scheduler_cycles",
    "priority_critical_dispatched",
    "priority_high_dispatched",
    "priority_normal_dispatched",
    "priority_low_dispatched",
    "priority_background_dispatched",
    "priority_aging_promotions",
    "dispatcher_backpressure_events",
    "dispatcher_throttled_events",
    "dispatcher_queue_depth",
    "queue_health_score",
    "worker_utilization",
    # Cluster Coordination Keys
    "cluster_epoch",
    "current_ring_version",
    "membership_changes",
    "cluster_nodes",
    "healthy_nodes",
    "leader_changes",
    "dispatcher_heartbeats",
    "dispatcher_failures",
    "leadership_acquisitions",
    "leadership_losses",
    "dispatcher_assignments",
    "dispatcher_load",
    "cluster_health_score",
    "cluster_uptime",
    # Distributed Tracing Keys
    "active_traces",
    "completed_traces",
    "failed_traces",
    "span_count",
    "average_trace_duration",
    "average_spans_per_trace",
    "trace_storage_size",
    "critical_path_duration",
    "slowest_trace",
    "slowest_component",
    "trace_search_requests",
    "trace_retention_cleanup",
    # Execution Intelligence Keys
    "execution_health_score",
    "root_causes_detected",
    "bottlenecks_detected",
    "recommendations_generated",
    "retry_patterns",
    "failure_patterns",
    "latency_patterns",
    "consumer_hotspots",
    "partition_hotspots",
    "worker_hotspots",
    "dispatcher_hotspots",
)

# Canonical map for alias normalization
_KEY_ALIASES = {
    "generated_keys": "idempotency_keys_generated",
}


class EventMetrics:
    """
    Thread-safe in-process event pipeline metrics.

    One instance is created at module level (`event_metrics`).  Import that
    singleton; do not instantiate this class directly.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._counters: Dict[str, int] = {k: 0 for k in _COUNTER_KEYS}
        self._counters["queue_health_score"] = 100
        self._counters["cluster_health_score"] = 100
        self._counters["cluster_epoch"] = 1
        self._counters["execution_health_score"] = 100

    def _canonical_key(self, key: str) -> str:
        return _KEY_ALIASES.get(key, key)

    def increment(self, key: str, amount: int = 1) -> None:
        """Atomically add *amount* to counter *key*."""
        canonical = self._canonical_key(key)
        if canonical not in self._counters:
            raise KeyError(f"Unknown metric key '{key}'. Valid keys: {_COUNTER_KEYS}")
        with self._lock:
            self._counters[canonical] += amount

    def decrement(self, key: str, amount: int = 1) -> None:
        """Atomically subtract *amount* from counter *key* (minimum 0)."""
        canonical = self._canonical_key(key)
        if canonical not in self._counters:
            raise KeyError(f"Unknown metric key '{key}'. Valid keys: {_COUNTER_KEYS}")
        with self._lock:
            self._counters[canonical] = max(0, self._counters[canonical] - amount)

    def set(self, key: str, value: int) -> None:
        """Atomically set counter *key* to *value*."""
        canonical = self._canonical_key(key)
        if canonical not in self._counters:
            raise KeyError(f"Unknown metric key '{key}'. Valid keys: {_COUNTER_KEYS}")
        with self._lock:
            self._counters[canonical] = value

    def record_idempotency_lookup(self, duration_ms: float) -> None:
        """Atomically records an idempotency DB lookup and adds its latency."""
        with self._lock:
            self._counters["idempotency_lookups"] += 1
            self._counters["idempotency_lookup_duration_ms_tot"] += int(round(duration_ms))

    def record_root_cause(self, count: int = 1) -> None:
        """Atomically records detected root cause failure count."""
        with self._lock:
            self._counters["root_causes_detected"] += count

    def record_bottlenecks(self, count: int = 1) -> None:
        """Atomically records detected bottlenecks count."""
        with self._lock:
            self._counters["bottlenecks_detected"] += count

    def record_recommendation(self, count: int = 1) -> None:
        """Atomically records generated recommendations count."""
        with self._lock:
            self._counters["recommendations_generated"] += count

    def snapshot(self) -> MetricsSnapshot:
        """Return an immutable point-in-time copy of all counters."""
        with self._lock:
            c = self._counters
            return MetricsSnapshot(
                events_processed=c["processed"],
                events_failed=c["failed"],
                events_retried=c["retried"],
                events_dead_lettered=c["dead_lettered"],
                events_replayed=c["replayed"],
                events_active_processing=c["active_processing"],
                dispatcher_cycles=c["dispatcher_cycles"],
                idempotency_keys_generated=c["idempotency_keys_generated"],
                duplicate_events_blocked=c["duplicate_events_blocked"],
                replay_bypasses=c["replay_bypasses"],
                uniqueness_conflicts=c["uniqueness_conflicts"],
                idempotency_lookups=c["idempotency_lookups"],
                idempotency_lookup_duration_ms_tot=c["idempotency_lookup_duration_ms_tot"],
                active_partitions=c["active_partitions"],
                waiting_partitions=c["waiting_partitions"],
                largest_partition=c["largest_partition"],
                partition_locks_acquired=c["partition_locks_acquired"],
                partition_locks_released=c["partition_locks_released"],
                partition_lock_conflicts=c["partition_lock_conflicts"],
                partition_lock_timeouts=c["partition_lock_timeouts"],
                scheduler_cycles=c["scheduler_cycles"],
                priority_critical_dispatched=c["priority_critical_dispatched"],
                priority_high_dispatched=c["priority_high_dispatched"],
                priority_normal_dispatched=c["priority_normal_dispatched"],
                priority_low_dispatched=c["priority_low_dispatched"],
                priority_background_dispatched=c["priority_background_dispatched"],
                priority_aging_promotions=c["priority_aging_promotions"],
                dispatcher_backpressure_events=c["dispatcher_backpressure_events"],
                dispatcher_throttled_events=c["dispatcher_throttled_events"],
                dispatcher_queue_depth=c["dispatcher_queue_depth"],
                queue_health_score=c["queue_health_score"],
                worker_utilization=c["worker_utilization"],
                cluster_epoch=c["cluster_epoch"],
                current_ring_version=c["current_ring_version"],
                membership_changes=c["membership_changes"],
                cluster_nodes=c["cluster_nodes"],
                healthy_nodes=c["healthy_nodes"],
                leader_changes=c["leader_changes"],
                dispatcher_heartbeats=c["dispatcher_heartbeats"],
                dispatcher_failures=c["dispatcher_failures"],
                leadership_acquisitions=c["leadership_acquisitions"],
                leadership_losses=c["leadership_losses"],
                dispatcher_assignments=c["dispatcher_assignments"],
                dispatcher_load=c["dispatcher_load"],
                cluster_health_score=c["cluster_health_score"],
                cluster_uptime=c["cluster_uptime"],
                active_traces=c["active_traces"],
                completed_traces=c["completed_traces"],
                failed_traces=c["failed_traces"],
                span_count=c["span_count"],
                average_trace_duration=c["average_trace_duration"],
                average_spans_per_trace=c["average_spans_per_trace"],
                trace_storage_size=c["trace_storage_size"],
                critical_path_duration=c["critical_path_duration"],
                slowest_trace=c["slowest_trace"],
                slowest_component=c["slowest_component"],
                trace_search_requests=c["trace_search_requests"],
                trace_retention_cleanup=c["trace_retention_cleanup"],
                execution_health_score=c["execution_health_score"],
                root_causes_detected=c["root_causes_detected"],
                bottlenecks_detected=c["bottlenecks_detected"],
                recommendations_generated=c["recommendations_generated"],
                retry_patterns=c["retry_patterns"],
                failure_patterns=c["failure_patterns"],
                latency_patterns=c["latency_patterns"],
                consumer_hotspots=c["consumer_hotspots"],
                partition_hotspots=c["partition_hotspots"],
                worker_hotspots=c["worker_hotspots"],
                dispatcher_hotspots=c["dispatcher_hotspots"],
            )

    def get_snapshot(self) -> MetricsSnapshot:
        """Alias for snapshot()."""
        return self.snapshot()

    def reset(self) -> None:
        """
        Zero every counter.

        For TEST ISOLATION ONLY.  Do not call in production code.
        """
        with self._lock:
            for key in _COUNTER_KEYS:
                self._counters[key] = 0
            self._counters["queue_health_score"] = 100
            self._counters["cluster_health_score"] = 100
            self._counters["cluster_epoch"] = 1
            self._counters["execution_health_score"] = 100


# ── Module-level singleton ─────────────────────────────────────────────────────

event_metrics: EventMetrics = EventMetrics()

