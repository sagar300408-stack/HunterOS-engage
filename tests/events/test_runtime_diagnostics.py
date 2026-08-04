"""
HunterOS Engage — Runtime Diagnostics & Live Monitoring Test Suite
tests/events/test_runtime_diagnostics.py

Comprehensive test suite verifying runtime diagnostics, subsystem inspection,
snapshot consistency, health evaluations, REST APIs, and read-only invariants.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import (
    LiveInspectionQuery,
    RuntimeHealthStatus,
    SubsystemType,
)
from app.events.diagnostics.workers import DefaultWorkerDiagnosticsCollector
from app.events.diagnostics.dispatchers import DefaultDispatcherDiagnosticsCollector
from app.events.diagnostics.queues import DefaultQueueDiagnosticsCollector
from app.events.diagnostics.partitions import DefaultPartitionDiagnosticsCollector
from app.events.diagnostics.locks import DefaultLockDiagnosticsCollector
from app.events.diagnostics.consumers import DefaultConsumerDiagnosticsCollector
from app.events.diagnostics.scheduler import DefaultSchedulerDiagnosticsCollector
from app.events.diagnostics.health import DefaultRuntimeHealthMonitor
from app.events.diagnostics.runtime import DefaultRuntimeSnapshotGenerator
from app.events.diagnostics.inspection import DefaultLiveInspectionService
from app.events.diagnostics.engine import DefaultDiagnosticsEngine
from app.events.diagnostics.validator import DiagnosticsStartupValidator
from app.events.observability.metrics import event_metrics
from app.main import app


@pytest.fixture(autouse=True)
def reset_metrics():
    event_metrics.reset()
    yield
    event_metrics.reset()


# ── 1. Snapshot Consistency & Observation Point Invariant ────────────────────

@pytest.mark.asyncio
async def test_snapshot_consistency_and_observation_point():
    """
    Validates that every RuntimeSnapshot is produced from a single logical
    observation point (consistent read) and that all child sections share the same
    snapshot_id and snapshot_timestamp.
    """
    engine = DefaultDiagnosticsEngine()
    snapshot = await engine.get_runtime_snapshot()

    assert snapshot.snapshot_id.startswith("snap_")
    assert isinstance(snapshot.snapshot_timestamp, datetime)
    assert snapshot.observation_window_ms >= 0.0

    # Verify every section carries the exact same observation point
    assert snapshot.workers.snapshot_id == snapshot.snapshot_id
    assert snapshot.workers.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.dispatchers.snapshot_id == snapshot.snapshot_id
    assert snapshot.dispatchers.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.queues.snapshot_id == snapshot.snapshot_id
    assert snapshot.queues.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.partitions.snapshot_id == snapshot.snapshot_id
    assert snapshot.partitions.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.locks.snapshot_id == snapshot.snapshot_id
    assert snapshot.locks.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.consumers.snapshot_id == snapshot.snapshot_id
    assert snapshot.consumers.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.scheduler.snapshot_id == snapshot.snapshot_id
    assert snapshot.scheduler.snapshot_timestamp == snapshot.snapshot_timestamp

    assert snapshot.health.snapshot_id == snapshot.snapshot_id
    assert snapshot.health.snapshot_timestamp == snapshot.snapshot_timestamp


# ── 2. Worker Diagnostics Collector ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_diagnostics_collector():
    """
    Validates worker heartbeat reporting, active/idle count calculation,
    utilization %, throughput, and execution durations.
    """
    collector = DefaultWorkerDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    # Register workers
    collector.record_worker_heartbeat(
        worker_id="worker_alpha",
        status="ACTIVE",
        current_task_id="task_101",
        current_event_id="evt_201",
        execution_duration_ms=45.5,
        completed_delta=10,
    )
    collector.record_worker_heartbeat(
        worker_id="worker_beta",
        status="IDLE",
        completed_delta=5,
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_w",
        snapshot_timestamp=now,
    )

    assert diag.total_workers == 2
    assert diag.active_workers == 1
    assert diag.idle_workers == 1
    assert diag.executing_events_count == 1
    assert diag.worker_utilization_pct == 50.0
    assert diag.average_execution_duration_ms == 45.5
    assert diag.worker_throughput_per_sec == 15.0
    assert diag.worker_failures_count == 0


# ── 3. Dispatcher Diagnostics Collector ──────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatcher_diagnostics_collector():
    """
    Validates dispatcher heartbeat, leader status, epoch, poll frequency,
    and partition ownership distribution.
    """
    collector = DefaultDispatcherDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    collector.record_dispatcher_heartbeat(
        dispatcher_id="dispatcher_01",
        is_leader=True,
        cluster_epoch=3,
        poll_frequency_sec=0.5,
        assigned_partitions_count=4,
        dispatched_delta=120,
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_d",
        snapshot_timestamp=now,
    )

    assert diag.active_dispatchers_count == 1
    assert diag.leader_dispatcher_id == "dispatcher_01"
    assert diag.cluster_epoch == 3
    assert diag.average_poll_frequency_sec == 0.5
    assert diag.dispatcher_ownership == {"dispatcher_01": 4}
    assert len(diag.dispatchers) == 1
    assert diag.dispatchers[0].is_leader is True


# ── 4. Queue Diagnostics Collector ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_diagnostics_collector():
    """
    Validates queue breakdown, total depth, dead-letter rate, and retry rate.
    """
    collector = DefaultQueueDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    event_metrics.increment("dead_lettered", 2)
    event_metrics.increment("processed", 98)
    event_metrics.increment("retried", 5)

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_q",
        snapshot_timestamp=now,
    )

    assert diag.breakdown.dead_letter == 2
    assert diag.breakdown.retrying == 5
    assert diag.dead_letter_rate == 2.0
    assert diag.throughput_per_sec == 98.0


# ── 5. Partition Diagnostics Collector ───────────────────────────────────────

@pytest.mark.asyncio
async def test_partition_diagnostics_collector():
    """
    Validates partition backlog, active vs waiting counts, and hottest partitions.
    """
    collector = DefaultPartitionDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    collector.record_partition_state(
        partition_key="tenant_123",
        state="ACTIVE",
        pending_events_count=15,
        oldest_event_age_sec=4.2,
    )
    collector.record_partition_state(
        partition_key="tenant_456",
        state="WAITING",
        pending_events_count=85,
        oldest_event_age_sec=18.5,
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_p",
        snapshot_timestamp=now,
    )

    assert diag.total_partitions == 2
    assert diag.active_partitions_count == 1
    assert diag.waiting_partitions_count == 1
    assert diag.total_partition_backlog == 100
    assert diag.oldest_event_age_sec == 18.5
    assert diag.hottest_partitions[0].partition_key == "tenant_456"
    assert diag.hottest_partitions[0].pending_events_count == 85


# ── 6. Lock Diagnostics Collector ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lock_diagnostics_collector():
    """
    Validates active lock leases, expiration tracking, owner distribution,
    and contention events.
    """
    collector = DefaultLockDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    collector.record_lock_lease(
        resource_id="partition_lock_workspace_1",
        owner_id="worker_alpha",
        expires_at=now + timedelta(seconds=20),
        remaining_lease_sec=20.0,
    )
    collector.record_lock_lease(
        resource_id="partition_lock_workspace_2",
        owner_id="worker_beta",
        expires_at=now - timedelta(seconds=5),  # expired
        remaining_lease_sec=0.0,
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_l",
        snapshot_timestamp=now,
    )

    assert diag.active_locks_count == 1
    assert diag.expired_locks_count == 1
    assert diag.lock_owners == {"worker_alpha": 1}
    assert diag.average_lease_duration_sec > 0.0


# ── 7. Consumer Diagnostics Collector ────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumer_diagnostics_collector():
    """
    Validates consumer execution counts, failure rates, latencies,
    and dependency graphs.
    """
    collector = DefaultConsumerDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    collector.record_consumer_execution(
        consumer_name="EmailNotificationConsumer",
        event_types=["user.registered"],
        duration_ms=50.0,
        is_failure=False,
        dependencies=["AuditLogConsumer"],
    )
    collector.record_consumer_execution(
        consumer_name="EmailNotificationConsumer",
        duration_ms=70.0,
        is_failure=True,
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_c",
        snapshot_timestamp=now,
    )

    assert diag.total_consumers_registered == 1
    assert diag.total_executions == 2
    assert diag.total_failures == 1
    assert diag.overall_average_latency_ms == 60.0
    assert diag.consumers[0].failure_rate == 50.0
    assert diag.consumer_dependency_graph == {"EmailNotificationConsumer": ["AuditLogConsumer"]}


# ── 8. Scheduler Diagnostics Collector ───────────────────────────────────────

@pytest.mark.asyncio
async def test_scheduler_diagnostics_collector():
    """
    Validates scheduler policy, deficit counters, and priority flow rates.
    """
    collector = DefaultSchedulerDiagnosticsCollector()
    now = datetime.now(timezone.utc)

    collector.record_scheduler_cycle(
        deficits={"tenant_1": 1500, "tenant_2": 800},
        flow_rates={"CRITICAL": 1.0, "NORMAL": 0.6},
    )

    diag = await collector.collect_diagnostics(
        snapshot_id="snap_test_s",
        snapshot_timestamp=now,
    )

    assert diag.scheduler_policy == "DeficitRoundRobin"
    assert diag.fairness_deficit_balance["tenant_1"] == 1500
    assert diag.priority_flow_rates["CRITICAL"] == 1.0
    assert diag.priority_flow_rates["NORMAL"] == 0.6


# ── 9. Runtime Health Monitor ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_runtime_health_monitor_healthy_and_degraded():
    """
    Validates multi-dimensional subsystem scoring, weighted overall health,
    and early warning indicator triggers under simulated degradation.
    """
    engine = DefaultDiagnosticsEngine()

    # Normal healthy snapshot
    snap_healthy = await engine.get_runtime_snapshot()
    assert snap_healthy.health.overall_score >= 80
    assert snap_healthy.health.overall_status == RuntimeHealthStatus.HEALTHY

    # Simulate degradation: Saturate workers + dead letter surge
    for i in range(10):
        engine.worker_collector.record_worker_heartbeat(
            worker_id=f"worker_{i}",
            status="ACTIVE",
            execution_duration_ms=100.0,
            failed_delta=3,
        )
    event_metrics.increment("dead_lettered", 50)
    event_metrics.increment("processed", 50)

    snap_degraded = await engine.get_runtime_snapshot()
    assert snap_degraded.health.overall_score < 80
    assert len(snap_degraded.health.early_warning_indicators) > 0

    # Confirm early warning contains actionable guidance
    warn = snap_degraded.health.early_warning_indicators[0]
    assert warn.severity in ("WARNING", "CRITICAL")
    assert len(warn.recommended_action) > 0


# ── 10. Live Inspection Service ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_live_inspection_service():
    """
    Validates targeted live inspection queries by subsystem, entity ID, and state.
    """
    engine = DefaultDiagnosticsEngine()
    engine.worker_collector.record_worker_heartbeat(
        worker_id="worker_target_99",
        status="ACTIVE",
    )
    engine.worker_collector.record_worker_heartbeat(
        worker_id="worker_other_01",
        status="IDLE",
    )

    # Inspect specific worker by ID
    query_id = LiveInspectionQuery(
        subsystem=SubsystemType.WORKERS,
        entity_id="worker_target_99",
    )
    res_id = await engine.inspect_subsystem(query_id)
    assert res_id.matched_count == 1
    assert res_id.details[0]["worker_id"] == "worker_target_99"

    # Inspect by state filter
    query_state = LiveInspectionQuery(
        subsystem=SubsystemType.WORKERS,
        filter_state="IDLE",
    )
    res_state = await engine.inspect_subsystem(query_state)
    assert any(w["worker_id"] == "worker_other_01" for w in res_state.details)


# ── 11. Metrics Integration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_diagnostics_metrics_integration():
    """
    Validates atomic metric increments and utilization updates during diagnostics operations.
    """
    engine = DefaultDiagnosticsEngine()

    assert event_metrics.snapshot().runtime_snapshot_requests == 0
    await engine.get_runtime_snapshot()
    assert event_metrics.snapshot().runtime_snapshot_requests == 1

    assert event_metrics.snapshot().diagnostic_queries == 0
    await engine.inspect_subsystem(LiveInspectionQuery(subsystem=SubsystemType.WORKERS))
    assert event_metrics.snapshot().diagnostic_queries == 1

    event_metrics.set_dispatcher_utilization(75)
    event_metrics.set_consumer_utilization(40)
    event_metrics.set_partition_utilization(30)
    event_metrics.set_queue_utilization(15)

    m = event_metrics.snapshot()
    assert m.dispatcher_utilization == 75
    assert m.consumer_utilization == 40
    assert m.partition_utilization == 30
    assert m.queue_utilization == 15


# ── 12. Startup Validator ────────────────────────────────────────────────────

def test_startup_validator():
    """
    Validates pre-flight startup validator verification.
    """
    engine = DefaultDiagnosticsEngine()
    validator = DiagnosticsStartupValidator(engine)
    # Sync validation
    validator.validate_sync()


# ── 13. REST Reliability Endpoints ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_reliability_api_runtime_endpoints():
    """
    Validates all 8 live diagnostics REST API endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Full Snapshot
        resp_snap = await client.get("/api/v1/reliability/runtime")
        assert resp_snap.status_code == 200
        snap_data = resp_snap.json()
        assert "snapshot_id" in snap_data
        assert "workers" in snap_data
        assert "dispatchers" in snap_data
        assert "queues" in snap_data
        assert "partitions" in snap_data
        assert "locks" in snap_data
        assert "consumers" in snap_data
        assert "health" in snap_data

        # 2. Workers
        resp_w = await client.get("/api/v1/reliability/runtime/workers")
        assert resp_w.status_code == 200
        assert "active_workers" in resp_w.json()

        # 3. Dispatchers
        resp_d = await client.get("/api/v1/reliability/runtime/dispatchers")
        assert resp_d.status_code == 200
        assert "active_dispatchers_count" in resp_d.json()

        # 4. Queues
        resp_q = await client.get("/api/v1/reliability/runtime/queues")
        assert resp_q.status_code == 200
        assert "breakdown" in resp_q.json()

        # 5. Partitions
        resp_p = await client.get("/api/v1/reliability/runtime/partitions")
        assert resp_p.status_code == 200
        assert "active_partitions_count" in resp_p.json()

        # 6. Locks
        resp_l = await client.get("/api/v1/reliability/runtime/locks")
        assert resp_l.status_code == 200
        assert "active_locks_count" in resp_l.json()

        # 7. Consumers
        resp_c = await client.get("/api/v1/reliability/runtime/consumers")
        assert resp_c.status_code == 200
        assert "total_consumers_registered" in resp_c.json()

        # 8. Health
        resp_h = await client.get("/api/v1/reliability/runtime/health")
        assert resp_h.status_code == 200
        assert "overall_score" in resp_h.json()
        assert "subsystem_health" in resp_h.json()


# ── 14. Read-Only Passivity & Failure Isolation Invariants ───────────────────

@pytest.mark.asyncio
async def test_diagnostics_read_only_invariants():
    """
    Verifies that diagnostics operations never mutate pipeline state or metrics counters unexpectedly.
    """
    engine = DefaultDiagnosticsEngine()
    m_before = event_metrics.snapshot()

    # Query all diagnostics
    await engine.get_runtime_snapshot()
    await engine.get_worker_diagnostics()
    await engine.get_dispatcher_diagnostics()
    await engine.get_queue_diagnostics()
    await engine.get_partition_diagnostics()
    await engine.get_lock_diagnostics()
    await engine.get_consumer_diagnostics()
    await engine.get_scheduler_diagnostics()
    await engine.get_runtime_health()

    m_after = event_metrics.snapshot()

    # Verify event execution counters remain unchanged
    assert m_after.events_processed == m_before.events_processed
    assert m_after.events_failed == m_before.events_failed
    assert m_after.events_retried == m_before.events_retried
    assert m_after.events_dead_lettered == m_before.events_dead_lettered
    assert m_after.events_replayed == m_before.events_replayed
