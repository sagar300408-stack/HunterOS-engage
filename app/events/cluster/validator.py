"""
Startup Diagnostic Validator for Distributed Dispatcher Cluster Coordination.
"""

from datetime import datetime, timezone, timedelta
import logging
from uuid import uuid4

from app.events.cluster.config import ClusterConfig
from app.events.cluster.cluster_scheduler import (
    ClusterDispatchCoordinator,
    DefaultConsistentHashRing,
)
from app.events.cluster.leader import LeaderElectionEngine
from app.events.cluster.lease import InMemoryDispatcherLeaseManager
from app.events.cluster.registry import DispatcherNode, InMemoryDispatcherRegistry

logger = logging.getLogger(__name__)


class ClusterStartupValidator:
    """
    Validates cluster coordination, consistent hash ring determinism, lease tokens,
    and leader election integrity during service startup.
    """

    @classmethod
    def validate(cls) -> None:
        logger.info("Executing ClusterStartupValidator diagnostics...")

        # 1. Validate Registry & Epoch Monotonicity
        registry = InMemoryDispatcherRegistry(initial_epoch=1)
        node_a = DispatcherNode(
            dispatcher_id="test-node-a",
            hostname="host-a",
            pid=1001,
            startup_timestamp=datetime.now(timezone.utc),
        )
        epoch_1 = registry.register(node_a)
        if epoch_1 <= 1:
            raise RuntimeError(f"ClusterStartupValidator failed: expected epoch > 1, got {epoch_1}")

        node_b = DispatcherNode(
            dispatcher_id="test-node-b",
            hostname="host-b",
            pid=1002,
            startup_timestamp=datetime.now(timezone.utc),
        )
        epoch_2 = registry.register(node_b)
        if epoch_2 <= epoch_1:
            raise RuntimeError(f"ClusterStartupValidator failed: epoch did not advance on node join ({epoch_2} <= {epoch_1})")

        # 2. Validate Lease Manager & Lease Token Integrity
        lease_mgr = InMemoryDispatcherLeaseManager()
        t0 = datetime.now(timezone.utc)
        token_a = lease_mgr.acquire_leadership("test-node-a", lease_seconds=10.0, now=t0)
        if not token_a or not isinstance(token_a, str):
            raise RuntimeError("ClusterStartupValidator failed: lease acquisition did not return valid token")

        # Node B cannot acquire while Node A holds unexpired lease
        token_b = lease_mgr.acquire_leadership("test-node-b", lease_seconds=10.0, now=t0)
        if token_b is not None:
            raise RuntimeError("ClusterStartupValidator failed: split-brain detected! Node B acquired locked lease")

        # Node A renewal succeeds
        renew_ok = lease_mgr.renew_leadership("test-node-a", token_a, lease_seconds=10.0, now=t0)
        if not renew_ok:
            raise RuntimeError("ClusterStartupValidator failed: leader renewal failed with valid token")

        # Expired lease is safely reclaimable by Node B
        t_expired = t0 + timedelta(seconds=11.0)
        token_b_reclaimed = lease_mgr.acquire_leadership("test-node-b", lease_seconds=10.0, now=t_expired)
        if not token_b_reclaimed:
            raise RuntimeError("ClusterStartupValidator failed: expired lease was not reclaimed by Node B")

        # 3. Validate Consistent Hash Ring Determinism
        ring_1 = DefaultConsistentHashRing(virtual_nodes=64)
        ring_2 = DefaultConsistentHashRing(virtual_nodes=64)

        nodes = ["dispatcher-1", "dispatcher-2", "dispatcher-3"]
        ring_1.rebuild(nodes)
        ring_2.rebuild(nodes)

        # Test 100 sample keys: both rings must return identical node assignments
        for i in range(100):
            sample_key = f"conversation:workspace-99:user-{i}"
            n1 = ring_1.get_node(sample_key)
            n2 = ring_2.get_node(sample_key)
            if n1 != n2 or n1 is None:
                raise RuntimeError(
                    f"ClusterStartupValidator failed: hash ring non-deterministic for key '{sample_key}' ({n1} != {n2})"
                )

        logger.info("ClusterStartupValidator diagnostics passed successfully.")
