"""
Exhaustive Automated Test Suite for HunterOS Distributed Dispatcher Cluster Coordination.
Tests:
  - AbstractConsistentHashRing Interface & Custom Ring Pluggability
  - Monotonic Cluster Epoch Versioning & Membership Audit
  - Single Dispatcher Startup & Leadership Acquisition
  - Multi-Node Cluster Deterministic Partitioning & Zero Duplicate Dispatches
  - Leader Crash, Lease Expiration & Automatic Failover
  - Follower Crash, Heartbeat Timeout & Dead Node Pruning
  - Graceful Shutdown & Instant Leadership Step-Down
  - Lease Token Security & Split-Brain Prevention
  - Elastic Dynamic Scaling & Minimal Ring Migration
  - High-Volume Stress Simulation (50,000 events across 20 nodes)
  - Reliability Cluster API Endpoint Integration
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import uuid
import pytest
from fastapi.testclient import TestClient

# Import domain models to satisfy SQLAlchemy declarative base mapper configuration
from app.domain.conversations.models import Base, Conversation
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

from app.events.cluster.config import ClusterConfig
from app.events.cluster.cluster_scheduler import (
    AbstractConsistentHashRing,
    ClusterDispatchCoordinator,
    DefaultConsistentHashRing,
    PartitionAssignmentPlan,
)
from app.events.cluster.coordinator import ClusterCoordinator
from app.events.cluster.heartbeat import HeartbeatManager
from app.events.cluster.leader import LeaderElectionEngine
from app.events.cluster.lease import InMemoryDispatcherLeaseManager, LeaderLease
from app.events.cluster.registry import (
    DispatcherNode,
    DispatcherStatus,
    InMemoryDispatcherRegistry,
)
from app.events.cluster.validator import ClusterStartupValidator
from app.events.observability.metrics import event_metrics
from app.events.store.models import EventRecord


def create_fake_record(
    event_id: Any = None,
    partition_key: Optional[str] = None,
    correlation_id: Any = None,
    event_name: str = "CustomerRepliedEvent",
) -> EventRecord:
    """Helper to generate minimal EventRecord for coordinator planning."""
    eid = event_id if isinstance(event_id, uuid.UUID) else (uuid.UUID(str(event_id)) if event_id and len(str(event_id)) == 36 else uuid.uuid4())
    cid = correlation_id if isinstance(correlation_id, uuid.UUID) else (uuid.UUID(str(correlation_id)) if correlation_id and len(str(correlation_id)) == 36 else uuid.uuid4())
    return EventRecord(
        event_id=eid,
        schema_version=1,
        occurred_at=datetime.now(timezone.utc),
        correlation_id=cid,
        workspace_id=uuid.uuid4(),
        actor_type="system",
        source_subsystem="test",
        category="conversation",
        event_name=event_name,
        payload={"message": "test"},
        metadata_payload={},
        lifecycle_state="PERSISTED",
        partition_key=partition_key,
        priority=0,
        trace_id=f"trace-{eid}",
    )


# ── Scenario 1: Interface-Driven Hash Ring Pluggability ────────────────────────

class CustomRendezvousHashRing(AbstractConsistentHashRing):
    """Custom mock ring implementing Highest Random Weight / Rendezvous Hashing."""
    def __init__(self):
        self._nodes = set()
        self._version = 0

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)
        self._version += 1

    def remove_node(self, node_id: str) -> None:
        self._nodes.discard(node_id)
        self._version += 1

    def rebuild(self, nodes: list) -> None:
        self._nodes = set(nodes)
        self._version += 1

    def get_node(self, key: str) -> str | None:
        if not self._nodes:
            return None
        sorted_nodes = sorted(list(self._nodes))
        return sorted_nodes[hash(key) % len(sorted_nodes)]

    def get_ring_version(self) -> int:
        return self._version

    def get_node_distribution(self, sample_keys: list) -> dict:
        dist = {n: 0 for n in self._nodes}
        for k in sample_keys:
            n = self.get_node(k)
            if n:
                dist[n] += 1
        return dist


def test_abstract_consistent_hash_ring_pluggability():
    """Verify that ClusterDispatchCoordinator accepts custom AbstractConsistentHashRing implementations."""
    custom_ring = CustomRendezvousHashRing()
    coordinator = ClusterDispatchCoordinator(ring=custom_ring)

    nodes = ["node-alpha", "node-beta", "node-gamma"]
    records = [
        create_fake_record(partition_key=f"conv-{i % 10}")
        for i in range(50)
    ]

    plan = coordinator.plan_local_assignments(
        candidate_records=records,
        local_dispatcher_id="node-alpha",
        healthy_nodes=nodes,
        cluster_epoch=42,
    )

    assert plan.cluster_epoch == 42
    assert plan.ring_version == custom_ring.get_ring_version()
    assert plan.total_candidates == 50
    assert 0 <= plan.local_owned_count <= 50
    for r in plan.assigned_events:
        pkey = r.partition_key or str(r.correlation_id or r.event_id)
        assert plan.ownership_map[pkey] == "node-alpha"


# ── Scenario 2: Monotonic Cluster Epoch Versioning ───────────────────────────

def test_cluster_epoch_monotonicity():
    """Verify cluster_epoch strictly increments on all membership transitions."""
    registry = InMemoryDispatcherRegistry(initial_epoch=1)
    assert registry.get_current_epoch() == 1
    assert registry.get_membership_changes() == 0

    # 1. Register node 1 (join)
    n1 = DispatcherNode("disp-1", "host-1", 101, datetime.now(timezone.utc))
    e1 = registry.register(n1)
    assert e1 == 2
    assert registry.get_membership_changes() == 1

    # 2. Register node 2 (join)
    n2 = DispatcherNode("disp-2", "host-2", 102, datetime.now(timezone.utc))
    e2 = registry.register(n2)
    assert e2 == 3
    assert registry.get_membership_changes() == 2

    # 3. Unregister node 1 (leave)
    e3 = registry.unregister("disp-1")
    assert e3 == 4
    assert registry.get_membership_changes() == 3

    # 4. Prune dead nodes
    old_time = datetime.now(timezone.utc) - timedelta(seconds=100)
    n3 = DispatcherNode("disp-3", "host-3", 103, old_time, last_heartbeat=old_time)
    registry.register(n3)
    e4 = registry.get_current_epoch()
    pruned = registry.prune_dead_nodes(timeout_seconds=10.0)
    assert "disp-3" in pruned
    e5 = registry.get_current_epoch()
    assert e5 > e4


# ── Scenario 3: Single Dispatcher Startup & Full Ownership ────────────────────

def test_single_dispatcher_startup_and_ownership():
    """Verify single dispatcher acquires leadership and 100% of event ownership."""
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()
    coordinator = ClusterCoordinator(
        dispatcher_id="dispatcher-solo",
        registry=registry,
        lease_manager=lease_mgr,
    )

    coordinator.start()
    assert coordinator.is_leader() is True

    records = [
        create_fake_record(partition_key=f"tenant-{i}")
        for i in range(20)
    ]

    plan = coordinator.plan_local_assignments(records)
    assert plan.total_candidates == 20
    assert plan.local_owned_count == 20
    assert len(plan.assigned_events) == 20
    assert plan.local_ownership_ratio == 1.0


# ── Scenario 4: Multi-Node Cluster & Zero Duplicate Ownership ─────────────────

def test_multi_node_zero_duplicate_dispatches():
    """
    Verify that across a 3-node cluster, each event in a batch of 1,000 events
    is assigned to EXACTLY ONE dispatcher instance (zero duplicates, 100% total coverage).
    """
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()

    disp1 = ClusterCoordinator("disp-1", registry=registry, lease_manager=lease_mgr)
    disp2 = ClusterCoordinator("disp-2", registry=registry, lease_manager=lease_mgr)
    disp3 = ClusterCoordinator("disp-3", registry=registry, lease_manager=lease_mgr)

    disp1.start()
    disp2.start()
    disp3.start()

    records = [
        create_fake_record(partition_key=f"workspace-partition-{i % 50}")
        for i in range(1000)
    ]

    plan1 = disp1.plan_local_assignments(records)
    plan2 = disp2.plan_local_assignments(records)
    plan3 = disp3.plan_local_assignments(records)

    assigned_ids_1 = {r.event_id for r in plan1.assigned_events}
    assigned_ids_2 = {r.event_id for r in plan2.assigned_events}
    assigned_ids_3 = {r.event_id for r in plan3.assigned_events}

    # 1. Zero duplicate dispatches across any pair of nodes
    assert assigned_ids_1.isdisjoint(assigned_ids_2)
    assert assigned_ids_1.isdisjoint(assigned_ids_3)
    assert assigned_ids_2.isdisjoint(assigned_ids_3)

    # 2. Total coverage equals 100% of candidate records
    total_assigned = len(assigned_ids_1) + len(assigned_ids_2) + len(assigned_ids_3)
    assert total_assigned == 1000

    # 3. Fair distribution among nodes
    assert len(assigned_ids_1) > 200
    assert len(assigned_ids_2) > 200
    assert len(assigned_ids_3) > 200


# ── Scenario 5: Leader Crash & Automatic Failover ─────────────────────────────

def test_leader_crash_and_automatic_failover():
    """Verify follower node acquires leadership after leader lease expiration without split-brain."""
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()
    config = ClusterConfig(leader_lease_seconds=5.0)

    leader = ClusterCoordinator("leader-1", registry=registry, lease_manager=lease_mgr, config=config)
    follower = ClusterCoordinator("follower-2", registry=registry, lease_manager=lease_mgr, config=config)

    t0 = datetime.now(timezone.utc)
    leader.start()
    follower.start()

    assert leader.is_leader() is True
    assert follower.is_leader() is False

    # Leader crashes: time advances past lease TTL
    t_crashed = t0 + timedelta(seconds=6.0)

    # Follower attempts election after crash
    follower_won = follower.leader_engine.attempt_election(now=t_crashed)
    assert follower_won is True
    assert follower.is_leader(now=t_crashed) is True
    assert follower.leader_engine.get_current_leader_id(now=t_crashed) == "follower-2"


# ── Scenario 6: Follower Crash & Dead Node Pruning ────────────────────────────

def test_dead_node_pruning_and_ring_rebalancing():
    """Verify dead follower node is pruned by leader and its partitions are automatically rebalanced."""
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()
    config = ClusterConfig(node_timeout_seconds=5.0)

    leader = ClusterCoordinator("leader-node", registry=registry, lease_manager=lease_mgr, config=config)
    worker = ClusterCoordinator("worker-node", registry=registry, lease_manager=lease_mgr, config=config)

    t0 = datetime.now(timezone.utc)
    leader.start()
    worker.start()

    assert len(registry.get_healthy_nodes(5.0, now=t0)) == 2

    # Worker stops heartbeating for 10 seconds
    t_after_crash = t0 + timedelta(seconds=10.0)

    # Leader executes heartbeat cycle
    leader.heartbeat_manager.execute_heartbeat_cycle(now=t_after_crash)

    # Worker should be pruned
    healthy = registry.get_healthy_nodes(5.0, now=t_after_crash)
    assert len(healthy) == 1
    assert healthy[0].dispatcher_id == "leader-node"

    # Leader now claims 100% of candidate partitions
    records = [create_fake_record(partition_key=f"part-{i}") for i in range(100)]
    plan = leader.plan_local_assignments(records, now=t_after_crash)
    assert plan.local_owned_count == 100


# ── Scenario 7: Graceful Shutdown & Step-Down ─────────────────────────────────

@pytest.mark.asyncio
async def test_graceful_shutdown_instant_failover():
    """Verify leader clean shutdown releases lease immediately and follower takes over instantly."""
    registry = InMemoryDispatcherRegistry()
    lease_mgr = InMemoryDispatcherLeaseManager()

    disp1 = ClusterCoordinator("disp-1", registry=registry, lease_manager=lease_mgr)
    disp2 = ClusterCoordinator("disp-2", registry=registry, lease_manager=lease_mgr)

    disp1.start()
    disp2.start()

    assert disp1.is_leader() is True

    # Gracefully stop disp1
    await disp1.stop()

    # disp1 is unregistered and lease is released
    assert registry.get_node("disp-1") is None
    assert lease_mgr.get_current_leader() is None

    # disp2 takes over immediately without waiting for lease TTL
    elected = disp2.leader_engine.attempt_election()
    assert elected is True
    assert disp2.is_leader() is True


# ── Scenario 8: Lease Token Security & Split Brain Prevention ──────────────────

def test_lease_token_security_split_brain_prevention():
    """Verify lease cannot be renewed or released with invalid lease tokens."""
    lease_mgr = InMemoryDispatcherLeaseManager()
    t0 = datetime.now(timezone.utc)

    token_1 = lease_mgr.acquire_leadership("node-1", lease_seconds=10.0, now=t0)
    assert token_1 is not None

    # Node 2 cannot renew with fake token
    assert lease_mgr.renew_leadership("node-2", "fake-token", 10.0, now=t0) is False

    # Node 2 cannot renew with Node 1's token
    assert lease_mgr.renew_leadership("node-2", token_1, 10.0, now=t0) is False

    # Node 2 cannot release Node 1's lease
    assert lease_mgr.release_leadership("node-2", token_1) is False
    assert lease_mgr.is_leader("node-1", now=t0) is True

    # Node 1 release with correct token succeeds
    assert lease_mgr.release_leadership("node-1", token_1) is True
    assert lease_mgr.get_current_leader(now=t0) is None


# ── Scenario 9: Elastic Dynamic Scaling & Minimal Migration ───────────────────

def test_elastic_scaling_minimal_key_migration():
    """Verify that adding a new node to a 4-node cluster moves approximately 1/5th (20%) of keys."""
    ring = DefaultConsistentHashRing(virtual_nodes=128)
    initial_nodes = ["node-1", "node-2", "node-3", "node-4"]
    ring.rebuild(initial_nodes)

    sample_keys = [f"tenant-partition-{i}" for i in range(1000)]
    initial_mapping = {k: ring.get_node(k) for k in sample_keys}

    # Add 5th node
    ring.add_node("node-5")
    new_mapping = {k: ring.get_node(k) for k in sample_keys}

    # Count migrated keys
    migrated_keys = sum(1 for k in sample_keys if initial_mapping[k] != new_mapping[k])
    migration_ratio = migrated_keys / len(sample_keys)

    # Theoretical expectation is ~1/5 (20% +/- 6%)
    assert 0.14 <= migration_ratio <= 0.28


# ── Scenario 10: High-Volume Stress Simulation ────────────────────────────────

def test_high_volume_stress_simulation():
    """
    Stress test with 50,000 events across 5,000 distinct partitions simulated
    across 20 dispatchers in a single cluster.
    """
    num_nodes = 20
    num_events = 50000
    node_ids = [f"dispatcher-{i:02d}" for i in range(num_nodes)]

    registry = InMemoryDispatcherRegistry()
    for nid in node_ids:
        node = DispatcherNode(nid, "host", 1000, datetime.now(timezone.utc))
        registry.register(node)

    coordinator = ClusterDispatchCoordinator()
    events = [
        create_fake_record(partition_key=f"part-{i % 5000}")
        for i in range(num_events)
    ]

    assignments = {}
    for nid in node_ids:
        plan = coordinator.plan_local_assignments(
            candidate_records=events,
            local_dispatcher_id=nid,
            healthy_nodes=node_ids,
            cluster_epoch=10,
        )
        for r in plan.assigned_events:
            assert r.event_id not in assignments, f"Duplicate assignment detected for event {r.event_id}"
            assignments[r.event_id] = nid

    # Assert 100% assignment, 0 duplicate, 0 unassigned
    assert len(assignments) == num_events


# ── Scenario 11: Reliability API Endpoint Integration ─────────────────────────

def test_reliability_cluster_api_endpoint(client: TestClient):
    """Verify GET /api/v1/reliability/cluster returns cluster metrics and health status."""
    event_metrics.set("cluster_epoch", 5)
    event_metrics.set("cluster_health_score", 95)
    event_metrics.set("cluster_nodes", 3)
    event_metrics.set("healthy_nodes", 3)

    resp = client.get("/api/v1/reliability/cluster")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "healthy"
    assert data["cluster_epoch"] == 5
    assert data["cluster_health_score"] == 95
    assert data["cluster_nodes_total"] == 3
    assert data["healthy_nodes_total"] == 3
