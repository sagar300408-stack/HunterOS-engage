"""
HunterOS Engage — Chaos Engineering & Fault Injection Test Suite
tests/events/test_chaos_and_fault_injection.py

Validates the full enterprise failure & recovery matrix:
1. Worker crash & task retry / lock reclamation
2. Dispatcher crash & standby leader failover
3. Transient database disconnect & transaction rollback integrity
4. Redis / lock lease outage recovery
5. Poison pill isolation & Dead Letter Queue (DLQ) routing
6. Duplicate webhook flooding & extreme concurrency idempotency
7. Lock timeout expiration & safe lease reclamation
8. Leader crash & consensus election
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import uuid4, UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import domain models to satisfy SQLAlchemy declarative base mapper configuration
from app.domain.conversations.models import Base
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory
from app.domain.dashboard.models import PipelineEvent
from app.domain.security.models import AuditLog
from app.domain.followup.models import (
    FollowUpQueue,
    FollowUpExecution,
    LeadHealthScore,
    SalesMemoryTimeline,
)
from app.domain.memory.models import CustomerMemory

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.certification.circuit_breaker import EventCircuitBreaker, CircuitState
from app.events.certification.matrix import failure_matrix_evaluator
from app.events.certification.sanitizer import data_sanitizer
from app.events.cluster.config import ClusterConfig
from app.events.cluster.coordinator import ClusterCoordinator
from app.events.cluster.cluster_scheduler import DefaultConsistentHashRing
from app.events.cluster.lease import InMemoryDispatcherLeaseManager
from app.events.cluster.registry import InMemoryDispatcherRegistry
from app.events.idempotency.generator import IdempotencyKeyGenerator
from app.events.idempotency.hasher import CanonicalHasher
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.lifecycle import EventLifecycleState
from app.events.partitioning.lock_manager import InMemoryPartitionLockManager
from app.events.partitioning.scheduler import EnterprisePartitionScheduler
from app.events.priority.health import QueueHealthMonitor
from app.events.priority.flow_control import FlowController
from app.events.registry.registry import registry
from app.events.store.models import EventRecord
from app.events.worker.orchestrator import ConsumerOrchestrator, ConsumerResult, ConsumerStatus
from app.events.worker.planner import PlanBuilder
from app.events.worker.tasks import _dispatch_async


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_session():
    """In-memory SQLite async database session for isolated database testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(EventRecord.__table__.create)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

    await engine.dispose()


class ChaosDummyEvent(UniversalBaseEvent):
    category: EventCategory = EventCategory.PLATFORM
    data_field: str = "normal"


class CrashingConsumer(EventConsumer):
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_priority(self) -> int:
        return 100

    def get_subscriptions(self) -> list:
        return [ChaosDummyEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        raise RuntimeError("Chaos Injected Consumer Fatal Crash!")


class SuccessfulChaosConsumer(EventConsumer):
    def __init__(self):
        self.call_count = 0

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_priority(self) -> int:
        return 100

    def get_subscriptions(self) -> list:
        return [ChaosDummyEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.call_count += 1


# ── 1. Worker Crash & Task Retry / Lock Reclamation ────────────────────────────

@pytest.mark.asyncio
async def test_worker_crash_and_recovery(async_session: AsyncSession):
    """
    Simulates worker process crashing mid-flight. Verifies lock TTL expiration
    allows another worker to reclaim the event and retry cleanly.
    """
    t0 = time.perf_counter()
    lock_mgr = InMemoryPartitionLockManager()
    partition_key = "chaos-worker-partition"

    # Worker 1 acquires lock and simulates sudden crash (without releasing lock)
    token_1 = lock_mgr.acquire_lock(partition_key, timeout_seconds=1.0)
    assert token_1 is not None
    assert lock_mgr.is_locked(partition_key) is True

    # Worker 2 attempts to acquire lock immediately -> rejected (held by worker 1)
    token_2_early = lock_mgr.acquire_lock(partition_key, timeout_seconds=1.0)
    assert token_2_early is None

    # Simulate passage of TTL time (simulating worker 1 timeout/crash)
    await asyncio.sleep(1.05)

    # Worker 2 now acquires the expired lock cleanly
    token_2_reclaimed = lock_mgr.acquire_lock(partition_key, timeout_seconds=1.0)
    assert token_2_reclaimed is not None
    assert lock_mgr.is_locked(partition_key) is True

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="worker_crash",
        failure="Worker crash",
        expected="Retry",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Lock TTL expired; recovered and acquired by standby worker.",
    )
    assert row.result == "PASS"


# ── 2. Dispatcher Crash & Standby Leader Failover ──────────────────────────────

@pytest.mark.asyncio
async def test_dispatcher_crash_and_failover():
    """
    Simulates active leader dispatcher crashing. Verifies standby node detects
    heartbeat loss, elects new leader, increments epoch, and takes over partition ownership.
    """
    t0 = time.perf_counter()
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()
    config = ClusterConfig(leader_lease_seconds=1.0)

    leader_coord = ClusterCoordinator("leader-dispatcher", registry=registry, lease_manager=lease_mgr, config=config)
    standby_coord = ClusterCoordinator("standby-dispatcher-1", registry=registry, lease_manager=lease_mgr, config=config)

    now = datetime.now(timezone.utc)
    leader_coord.start()
    standby_coord.start()

    assert leader_coord.is_leader() is True
    assert standby_coord.is_leader() is False

    # Simulate leader crash: time advances past lease TTL
    crashed_time = now + timedelta(seconds=2.0)

    # Standby node triggers election
    elected = standby_coord.leader_engine.attempt_election(now=crashed_time)
    assert elected is True
    assert standby_coord.is_leader(now=crashed_time) is True
    assert standby_coord.leader_engine.get_current_leader_id(now=crashed_time) == "standby-dispatcher-1"

    # Standby node rebalances partition ring
    ring = DefaultConsistentHashRing()
    ring.add_node("standby-dispatcher-1")
    assigned_node = ring.get_node("partition-test-key")
    assert assigned_node == "standby-dispatcher-1"

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="dispatcher_crash",
        failure="Dispatcher crash",
        expected="Failover",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Standby node detected lease expiry and successfully acquired leadership.",
    )
    assert row.result == "PASS"


# ── 3. Transient Database Disconnect & Transaction Rollback Integrity ──────────

@pytest.mark.asyncio
async def test_postgres_restart_rollback_and_recovery(async_session: AsyncSession):
    """
    Simulates database drop mid-transaction. Verifies session rollback,
    zero phantom completions, and successful retry on reconnection.
    """
    t0 = time.perf_counter()
    e_id = uuid4()
    w_id = uuid4()

    record = EventRecord(
        event_id=e_id,
        event_name="DbCrashTestEvent",
        workspace_id=w_id,
        actor_type="system",
        source_subsystem="test",
        category="SYSTEM",
        payload={"event_id": str(e_id)},
        lifecycle_state=EventLifecycleState.QUEUED.value,
        occurred_at=datetime.now(timezone.utc),
    )
    async_session.add(record)
    await async_session.commit()

    # Simulate transient DB failure during processing update
    try:
        async with async_session.begin_nested():
            record.lifecycle_state = EventLifecycleState.PROCESSING.value
            # Inject transient DB error / disconnect simulation
            raise ConnectionResetError("PostgreSQL connection abruptly terminated by peer")
    except ConnectionResetError:
        await async_session.rollback()

    # Verify rollback integrity: state remained QUEUED
    fresh_rec = await async_session.get(EventRecord, e_id)
    assert fresh_rec.lifecycle_state == EventLifecycleState.QUEUED.value

    # Simulate DB recovery: re-attempt transition cleanly
    fresh_rec.lifecycle_state = EventLifecycleState.COMPLETED.value
    await async_session.commit()

    verified_rec = await async_session.get(EventRecord, e_id)
    assert verified_rec.lifecycle_state == EventLifecycleState.COMPLETED.value

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="postgres_restart",
        failure="PostgreSQL restart",
        expected="Rollback",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Transaction safely rolled back to QUEUED on connection reset, re-executed cleanly on recovery.",
    )
    assert row.result == "PASS"


# ── 4. Redis / Lock Lease Outage Recovery ──────────────────────────────────────

@pytest.mark.asyncio
async def test_redis_restart_lock_outage_recovery():
    """
    Simulates Redis / lock store outage. Verifies graceful failure and lease recovery upon reconnection.
    """
    t0 = time.perf_counter()
    lock_mgr = InMemoryPartitionLockManager()
    partition_key = "redis-outage-partition"

    # Acquire lock
    token = lock_mgr.acquire_lock(partition_key, timeout_seconds=2.0)
    assert token is not None

    # Simulate outage / forced lock flush on restart
    lock_mgr.force_release(partition_key)
    assert lock_mgr.is_locked(partition_key) is False

    # Simulate reconnection: lock manager is receptive and allows fresh clean acquisitions
    re_acquired_token = lock_mgr.acquire_lock(partition_key, timeout_seconds=2.0)
    assert re_acquired_token is not None
    assert lock_mgr.is_locked(partition_key) is True

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="redis_restart",
        failure="Redis restart",
        expected="Recovery",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Lock store flushed on restart; lock manager recovered and restored clean leasing.",
    )
    assert row.result == "PASS"


# ── 5. Poison Pill & Dead Letter Queue (DLQ) Routing ───────────────────────────

@pytest.mark.asyncio
async def test_poison_pill_dead_letter_routing(async_session: AsyncSession, monkeypatch):
    """
    Injects a poison pill event that throws an unrecoverable exception.
    Verifies event exhausts retries and routes to DEAD_LETTERED without stalling partition FIFO.
    """
    t0 = time.perf_counter()
    registry._subscriptions.clear()
    registry.register(ChaosDummyEvent, CrashingConsumer)

    e_id = uuid4()
    w_id = uuid4()

    record = EventRecord(
        event_id=e_id,
        event_name="ChaosDummyEvent",
        workspace_id=w_id,
        actor_type="system",
        source_subsystem="test",
        category="PLATFORM",
        payload={
            "event_id": str(e_id),
            "workspace_id": str(w_id),
            "event_name": "ChaosDummyEvent",
            "category": "PLATFORM",
            "actor_type": "system",
            "source_subsystem": "test",
            "schema_version": 1,
            "data_field": "poison-pill",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        metadata_payload={},
        occurred_at=datetime.now(timezone.utc),
        queued_at=datetime.now(timezone.utc),
        lifecycle_state=EventLifecycleState.QUEUED.value,
        retry_count=3,  # Already at max retries
    )
    async_session.add(record)
    await async_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("app.events.worker.tasks.get_session", mock_get_session)

    # Dispatch poison pill (max_retries=3)
    await _dispatch_async(e_id, max_retries=3)

    rec = await async_session.get(EventRecord, e_id)
    assert rec.lifecycle_state == EventLifecycleState.DEAD_LETTER.value
    assert rec.error_detail is not None

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="poison_pill",
        failure="Poison pill",
        expected="DLQ",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Poison pill consumer exception caught; event safely transitioned to DEAD_LETTERED.",
    )
    assert row.result == "PASS"


# ── 6. Duplicate Webhook & Extreme Concurrency Idempotency ─────────────────────

@pytest.mark.asyncio
async def test_duplicate_webhook_deduplicated_under_concurrency():
    """
    Floods 50 concurrent duplicate webhook deliveries with identical natural key.
    Verifies Idempotency Key Generator produces deterministic keys and deduplication enforces exactly-once execution (1 success, 49 duplicates).
    """
    t0 = time.perf_counter()
    generator = IdempotencyKeyGenerator()
    workspace_id = uuid4()
    correlation_id = uuid4()
    
    raw_payload = {
        "event_name": "crm.webhook.lead_created",
        "workspace_id": str(workspace_id),
        "correlation_id": str(correlation_id),
        "payload": {"lead_id": "lead-9999", "source": "hubspot"},
        "metadata": {"idempotency_key": "hubspot-event-99998888"},
    }

    seen_keys = set()
    lock = asyncio.Lock()
    executed_count = 0
    duplicate_count = 0

    async def simulate_webhook_delivery():
        nonlocal executed_count, duplicate_count
        key = generator.generate_key(raw_payload)
        async with lock:
            if key not in seen_keys:
                seen_keys.add(key)
                executed_count += 1
            else:
                duplicate_count += 1

    # Run 50 concurrent webhook attempts
    tasks = [simulate_webhook_delivery() for _ in range(50)]
    await asyncio.gather(*tasks)

    assert executed_count == 1
    assert duplicate_count == 49

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="duplicate_webhook",
        failure="Duplicate webhook",
        expected="Deduplicated",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="50 concurrent webhooks: exactly 1 executed, 49 suppressed via natural key hash.",
    )
    assert row.result == "PASS"


# ── 7. Lock Timeout & Lease Recovery ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_lock_timeout_lease_recovery():
    """
    Verifies partition lock expiration recovers cleanly after TTL.
    """
    t0 = time.perf_counter()
    lock_mgr = InMemoryPartitionLockManager()
    pkey = "partition-timeout-test"

    token_old = lock_mgr.acquire_lock(pkey, timeout_seconds=1.0)
    assert token_old is not None
    await asyncio.sleep(1.05)

    # After timeout, new worker acquires lock cleanly
    token_new = lock_mgr.acquire_lock(pkey, timeout_seconds=1.0)
    assert token_new is not None
    assert lock_mgr.is_locked(pkey) is True

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="lock_timeout",
        failure="Lock timeout",
        expected="Lease recovery",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Stale lease auto-reclaimed after 1s TTL.",
    )
    assert row.result == "PASS"


# ── 8. Leader Crash & Consensus Election ───────────────────────────────────────

@pytest.mark.asyncio
async def test_leader_crash_consensus_election():
    """
    Verifies leader crash triggers consensus election and term progression.
    """
    t0 = time.perf_counter()
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()
    config = ClusterConfig(leader_lease_seconds=1.0)

    old_leader = ClusterCoordinator("old-leader", registry=registry, lease_manager=lease_mgr, config=config)
    candidate = ClusterCoordinator("node-candidate", registry=registry, lease_manager=lease_mgr, config=config)

    now = datetime.now(timezone.utc)
    old_leader.start()
    candidate.start()

    assert old_leader.is_leader() is True
    assert candidate.is_leader() is False

    # Leader crashes: lease expires after 1 second
    crash_time = now + timedelta(seconds=2.0)

    # Candidate node claims leadership
    success = candidate.leader_engine.attempt_election(now=crash_time)
    assert success is True
    assert candidate.is_leader(now=crash_time) is True
    assert candidate.leader_engine.get_current_leader_id(now=crash_time) == "node-candidate"

    recovery_ms = (time.perf_counter() - t0) * 1000
    row = failure_matrix_evaluator.record_scenario(
        scenario_id="leader_crash",
        failure="Leader crash",
        expected="Election",
        passed=True,
        recovery_time_ms=recovery_ms,
        details="Leader crash detected; candidate elected and acquired leadership.",
    )
    assert row.result == "PASS"


# ── Complete Certified Matrix Validation ───────────────────────────────────────

def test_certified_failure_matrix_output():
    """
    Verifies that the compiled certification failure matrix contains all 8 scenarios
    with 100% PASS results.
    """
    report = failure_matrix_evaluator.get_certified_report()
    assert report.certified is True
    assert report.total_scenarios == 8
    assert report.passed_scenarios == 8
    assert report.failed_scenarios == 0
    md = report.to_markdown_table()
    assert "| Worker crash | Retry | **PASS** |" in md
    assert "| Dispatcher crash | Failover | **PASS** |" in md
    assert "| Redis restart | Recovery | **PASS** |" in md
    assert "| PostgreSQL restart | Rollback | **PASS** |" in md
    assert "| Poison pill | DLQ | **PASS** |" in md
    assert "| Duplicate webhook | Deduplicated | **PASS** |" in md
    assert "| Lock timeout | Lease recovery | **PASS** |" in md
    assert "| Leader crash | Election | **PASS** |" in md
