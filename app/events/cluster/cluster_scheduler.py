"""
Interface-Driven Consistent Hashing Ring & Cluster Dispatch Scheduler for HunterOS Engage.
"""

from abc import ABC, abstractmethod
import bisect
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set

from app.events.cluster.config import ClusterConfig
from app.events.store.models import EventRecord

logger = logging.getLogger(__name__)


class AbstractConsistentHashRing(ABC):
    """
    Abstract interface for Consistent Hash Rings.
    ClusterDispatchCoordinator depends exclusively on this interface, allowing
    future algorithms (Rendezvous Hashing, Jump Consistent Hash, CRUSH, Topology-aware rings)
    to be plugged in seamlessly.
    """

    @abstractmethod
    def add_node(self, node_id: str) -> None:
        """Adds a dispatcher node to the consistent hash ring."""
        pass

    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        """Removes a dispatcher node from the consistent hash ring."""
        pass

    @abstractmethod
    def rebuild(self, nodes: List[str]) -> None:
        """Rebuilds the entire ring with the specified list of active nodes."""
        pass

    @abstractmethod
    def get_node(self, key: str) -> Optional[str]:
        """
        Maps a partition or event key to a single assigned dispatcher node ID.
        Returns None if the ring is empty.
        """
        pass

    @abstractmethod
    def get_ring_version(self) -> int:
        """Returns the monotonically increasing version of the ring."""
        pass

    @abstractmethod
    def get_node_distribution(self, sample_keys: List[str]) -> Dict[str, int]:
        """Returns ownership counts across nodes for the provided sample keys."""
        pass


class DefaultConsistentHashRing(AbstractConsistentHashRing):
    """
    Production-grade consistent hash ring with configurable virtual nodes per dispatcher.
    Uses fast 64-bit integer hashing and bisect binary search for sub-microsecond O(log N) lookups.
    """

    def __init__(
        self,
        virtual_nodes: int = 128,
        hash_algorithm: str = "md5",
    ):
        self.virtual_nodes = virtual_nodes
        self.hash_algorithm = hash_algorithm
        self._ring: List[int] = []  # Sorted list of virtual node hash values
        self._ring_nodes: List[str] = []  # Parallel list of assigned physical dispatcher_id
        self._ring_map: Dict[int, str] = {}  # hash_val -> physical dispatcher_id
        self._nodes: Set[str] = set()
        self._ring_version: int = 0

    def _hash(self, key: Any) -> int:
        if hasattr(key, "int"):
            return key.int & 0xFFFFFFFFFFFFFFFF
        if isinstance(key, bytes):
            b = key
        elif isinstance(key, str):
            b = key.encode("utf-8")
        elif hasattr(key, "bytes"):
            b = key.bytes
        else:
            b = str(key).encode("utf-8")

        if self.hash_algorithm == "md5":
            return int.from_bytes(hashlib.md5(b).digest()[:8], "big")
        elif self.hash_algorithm == "sha256":
            return int.from_bytes(hashlib.sha256(b).digest()[:8], "big")
        hasher = getattr(hashlib, self.hash_algorithm, hashlib.sha256)()
        hasher.update(b)
        return int.from_bytes(hasher.digest()[:8], "big")

    def _sync_ring(self) -> None:
        """Rebuilds the sorted parallel ring arrays."""
        sorted_pairs = sorted(self._ring_map.items(), key=lambda x: x[0])
        self._ring = [h for h, _ in sorted_pairs]
        self._ring_nodes = [node for _, node in sorted_pairs]

    def add_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            return
        self._nodes.add(node_id)
        for i in range(self.virtual_nodes):
            vnode_key = f"{node_id}#vnode_{i}"
            h = self._hash(vnode_key)
            self._ring_map[h] = node_id
        self._sync_ring()
        self._ring_version += 1

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            return
        self._nodes.remove(node_id)
        self._ring_map = {}
        for remaining in self._nodes:
            for i in range(self.virtual_nodes):
                vnode_key = f"{remaining}#vnode_{i}"
                h = self._hash(vnode_key)
                self._ring_map[h] = remaining
        self._sync_ring()
        self._ring_version += 1

    def rebuild(self, nodes: List[str]) -> None:
        current_set = set(nodes)
        if current_set == self._nodes:
            return  # No change in membership
        self._nodes = set(nodes)
        self._ring_map = {}
        for node_id in self._nodes:
            for i in range(self.virtual_nodes):
                vnode_key = f"{node_id}#vnode_{i}"
                h = self._hash(vnode_key)
                self._ring_map[h] = node_id
        self._sync_ring()
        self._ring_version += 1

    def get_node(self, key: str) -> Optional[str]:
        if not self._ring:
            return None
        h = self._hash(key)
        idx = bisect.bisect_right(self._ring, h)
        if idx == len(self._ring):
            idx = 0  # Wrap around the ring
        return self._ring_nodes[idx]

    def get_ring_version(self) -> int:
        return self._ring_version

    def get_node_distribution(self, sample_keys: List[str]) -> Dict[str, int]:
        dist: Dict[str, int] = {node_id: 0 for node_id in self._nodes}
        for key in sample_keys:
            assigned = self.get_node(key)
            if assigned:
                dist[assigned] = dist.get(assigned, 0) + 1
        return dist


@dataclass(frozen=True)
class PartitionAssignmentPlan:
    """
    Immutable plan representing the cluster ownership evaluation for a batch of candidate events.
    Carries the cluster_epoch and ring_version for deterministic auditing and tracing.
    """
    cluster_epoch: int
    ring_version: int
    assigned_events: List[EventRecord]
    ownership_map: Dict[str, str]  # event_key -> assigned_dispatcher_id
    total_candidates: int
    local_owned_count: int
    healthy_node_ids: List[str]

    @property
    def local_ownership_ratio(self) -> float:
        if self.total_candidates == 0:
            return 1.0
        return self.local_owned_count / self.total_candidates


class ClusterDispatchCoordinator:
    """
    Pure planning engine for multi-dispatcher cluster coordination.
    Computes deterministic partition ownership over an AbstractConsistentHashRing.
    Never executes tasks or dispatches directly to Celery.
    """

    def __init__(
        self,
        ring: Optional[AbstractConsistentHashRing] = None,
        config: Optional[ClusterConfig] = None,
    ):
        self.config = config or ClusterConfig()
        self.ring = ring or DefaultConsistentHashRing(
            virtual_nodes=self.config.virtual_nodes_per_dispatcher,
            hash_algorithm=self.config.ownership_hash_algorithm,
        )

    def plan_local_assignments(
        self,
        candidate_records: List[EventRecord],
        local_dispatcher_id: str,
        healthy_nodes: List[str],
        cluster_epoch: int = 1,
    ) -> PartitionAssignmentPlan:
        """
        Determines which candidate records are owned by the local dispatcher.
        Guarantees deterministic, collision-free partitioning across all cluster nodes.
        """
        if not candidate_records:
            return PartitionAssignmentPlan(
                cluster_epoch=cluster_epoch,
                ring_version=self.ring.get_ring_version(),
                assigned_events=[],
                ownership_map={},
                total_candidates=0,
                local_owned_count=0,
                healthy_node_ids=list(healthy_nodes),
            )

        # 1. If only local node is active (or empty list provided), local node owns 100%
        if not healthy_nodes or (len(healthy_nodes) == 1 and healthy_nodes[0] == local_dispatcher_id):
            ownership_map = {
                (r.partition_key or str(r.correlation_id or r.event_id)): local_dispatcher_id
                for r in candidate_records
            }
            return PartitionAssignmentPlan(
                cluster_epoch=cluster_epoch,
                ring_version=self.ring.get_ring_version(),
                assigned_events=list(candidate_records),
                ownership_map=ownership_map,
                total_candidates=len(candidate_records),
                local_owned_count=len(candidate_records),
                healthy_node_ids=[local_dispatcher_id] if not healthy_nodes else list(healthy_nodes),
            )

        # 2. Synchronize ring membership
        self.ring.rebuild(healthy_nodes)

        # 3. Evaluate deterministic ownership for each record
        assigned_events: List[EventRecord] = []
        ownership_map: Dict[str, str] = {}

        for record in candidate_records:
            routing_key = (
                record.partition_key
                or str(record.correlation_id or record.event_id)
            )
            assigned_dispatcher = self.ring.get_node(routing_key)
            if assigned_dispatcher:
                ownership_map[routing_key] = assigned_dispatcher
                if assigned_dispatcher == local_dispatcher_id:
                    assigned_events.append(record)

        return PartitionAssignmentPlan(
            cluster_epoch=cluster_epoch,
            ring_version=self.ring.get_ring_version(),
            assigned_events=assigned_events,
            ownership_map=ownership_map,
            total_candidates=len(candidate_records),
            local_owned_count=len(assigned_events),
            healthy_node_ids=list(healthy_nodes),
        )
