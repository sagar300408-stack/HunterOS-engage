"""
Dispatcher Node Registry & Membership Tracking for HunterOS Distributed Dispatcher.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DispatcherStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    DEAD = "DEAD"


@dataclass
class DispatcherNode:
    """
    Metadata representation of an individual dispatcher instance in the cluster.
    """
    dispatcher_id: str
    hostname: str
    pid: int
    startup_timestamp: datetime
    version: str = "1.0.0"
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: DispatcherStatus = DispatcherStatus.ACTIVE
    is_leader: bool = False
    active_dispatch_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self, timeout_seconds: float, now: Optional[datetime] = None) -> bool:
        """Returns True if the node is ACTIVE and has heartbeated within the timeout window."""
        if self.status != DispatcherStatus.ACTIVE:
            return False
        current_time = now or datetime.now(timezone.utc)
        elapsed = (current_time - self.last_heartbeat).total_seconds()
        return elapsed <= timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Serializes node metadata to a dictionary."""
        return {
            "dispatcher_id": self.dispatcher_id,
            "hostname": self.hostname,
            "pid": self.pid,
            "startup_timestamp": self.startup_timestamp.isoformat(),
            "version": self.version,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "status": self.status.value,
            "is_leader": self.is_leader,
            "active_dispatch_count": self.active_dispatch_count,
            "metadata": self.metadata,
        }


class AbstractDispatcherRegistry(ABC):
    """
    Abstract interface for Dispatcher Cluster Registry.
    Guarantees pluggability across in-memory, PostgreSQL, Redis, or etcd backends.
    """

    @abstractmethod
    def register(self, node: DispatcherNode) -> int:
        """
        Registers a new dispatcher node into the cluster.
        Returns the updated cluster_epoch.
        """
        pass

    @abstractmethod
    def heartbeat(
        self,
        dispatcher_id: str,
        active_dispatch_count: int = 0,
        now: Optional[datetime] = None,
    ) -> bool:
        """
        Updates the last_heartbeat timestamp and active dispatch count for a node.
        Returns True if the node was found and updated, False otherwise.
        """
        pass

    @abstractmethod
    def unregister(self, dispatcher_id: str) -> int:
        """
        Unregisters a dispatcher node from the cluster.
        Returns the updated cluster_epoch.
        """
        pass

    @abstractmethod
    def get_node(self, dispatcher_id: str) -> Optional[DispatcherNode]:
        """Returns the DispatcherNode instance if found, or None."""
        pass

    @abstractmethod
    def get_cluster(self) -> List[DispatcherNode]:
        """Returns a snapshot list of all registered dispatcher nodes in the cluster."""
        pass

    @abstractmethod
    def get_healthy_nodes(
        self, timeout_seconds: float, now: Optional[datetime] = None
    ) -> List[DispatcherNode]:
        """Returns a list of all currently healthy and active dispatcher nodes."""
        pass

    @abstractmethod
    def prune_dead_nodes(
        self, timeout_seconds: float, now: Optional[datetime] = None
    ) -> List[str]:
        """
        Removes or marks dead nodes that have exceeded the timeout window.
        Returns the list of pruned dispatcher_ids.
        """
        pass

    @abstractmethod
    def get_current_epoch(self) -> int:
        """Returns the current monotonically increasing cluster epoch."""
        pass

    @abstractmethod
    def increment_epoch(self, reason: str = "") -> int:
        """Explicitly increments the cluster epoch due to cluster state transitions."""
        pass

    @abstractmethod
    def get_membership_changes(self) -> int:
        """Returns the total number of membership change events recorded."""
        pass


class InMemoryDispatcherRegistry(AbstractDispatcherRegistry):
    """
    Thread-safe in-memory dispatcher registry with cluster epoch tracking.
    """

    def __init__(self, initial_epoch: int = 1):
        self._lock = threading.RLock()
        self._nodes: Dict[str, DispatcherNode] = {}
        self._cluster_epoch: int = initial_epoch
        self._membership_changes: int = 0

    def register(self, node: DispatcherNode) -> int:
        with self._lock:
            existing = self._nodes.get(node.dispatcher_id)
            self._nodes[node.dispatcher_id] = node
            if existing is None or existing.status != node.status:
                self._cluster_epoch += 1
                self._membership_changes += 1
                logger.info(
                    f"Dispatcher node '{node.dispatcher_id}' registered. "
                    f"Cluster epoch advanced to {self._cluster_epoch}."
                )
            return self._cluster_epoch

    def heartbeat(
        self,
        dispatcher_id: str,
        active_dispatch_count: int = 0,
        now: Optional[datetime] = None,
    ) -> bool:
        with self._lock:
            node = self._nodes.get(dispatcher_id)
            if not node:
                return False
            node.last_heartbeat = now or datetime.now(timezone.utc)
            node.active_dispatch_count = active_dispatch_count
            if node.status == DispatcherStatus.DEAD:
                node.status = DispatcherStatus.ACTIVE
                self._cluster_epoch += 1
                self._membership_changes += 1
            return True

    def unregister(self, dispatcher_id: str) -> int:
        with self._lock:
            if dispatcher_id in self._nodes:
                del self._nodes[dispatcher_id]
                self._cluster_epoch += 1
                self._membership_changes += 1
                logger.info(
                    f"Dispatcher node '{dispatcher_id}' unregistered. "
                    f"Cluster epoch advanced to {self._cluster_epoch}."
                )
            return self._cluster_epoch

    def get_node(self, dispatcher_id: str) -> Optional[DispatcherNode]:
        with self._lock:
            node = self._nodes.get(dispatcher_id)
            if not node:
                return None
            # Return shallow copy
            return DispatcherNode(
                dispatcher_id=node.dispatcher_id,
                hostname=node.hostname,
                pid=node.pid,
                startup_timestamp=node.startup_timestamp,
                version=node.version,
                last_heartbeat=node.last_heartbeat,
                status=node.status,
                is_leader=node.is_leader,
                active_dispatch_count=node.active_dispatch_count,
                metadata=dict(node.metadata),
            )

    def get_cluster(self) -> List[DispatcherNode]:
        with self._lock:
            return [
                DispatcherNode(
                    dispatcher_id=n.dispatcher_id,
                    hostname=n.hostname,
                    pid=n.pid,
                    startup_timestamp=n.startup_timestamp,
                    version=n.version,
                    last_heartbeat=n.last_heartbeat,
                    status=n.status,
                    is_leader=n.is_leader,
                    active_dispatch_count=n.active_dispatch_count,
                    metadata=dict(n.metadata),
                )
                for n in self._nodes.values()
            ]

    def get_healthy_nodes(
        self, timeout_seconds: float, now: Optional[datetime] = None
    ) -> List[DispatcherNode]:
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            return [
                DispatcherNode(
                    dispatcher_id=n.dispatcher_id,
                    hostname=n.hostname,
                    pid=n.pid,
                    startup_timestamp=n.startup_timestamp,
                    version=n.version,
                    last_heartbeat=n.last_heartbeat,
                    status=n.status,
                    is_leader=n.is_leader,
                    active_dispatch_count=n.active_dispatch_count,
                    metadata=dict(n.metadata),
                )
                for n in self._nodes.values()
                if n.is_healthy(timeout_seconds, now=current_time)
            ]

    def prune_dead_nodes(
        self, timeout_seconds: float, now: Optional[datetime] = None
    ) -> List[str]:
        current_time = now or datetime.now(timezone.utc)
        pruned: List[str] = []
        with self._lock:
            for node_id, node in list(self._nodes.items()):
                if not node.is_healthy(timeout_seconds, now=current_time):
                    del self._nodes[node_id]
                    pruned.append(node_id)

            if pruned:
                self._cluster_epoch += 1
                self._membership_changes += len(pruned)
                logger.warning(
                    f"Pruned dead dispatcher nodes {pruned}. "
                    f"Cluster epoch advanced to {self._cluster_epoch}."
                )
        return pruned

    def get_current_epoch(self) -> int:
        with self._lock:
            return self._cluster_epoch

    def increment_epoch(self, reason: str = "") -> int:
        with self._lock:
            self._cluster_epoch += 1
            self._membership_changes += 1
            if reason:
                logger.info(
                    f"Cluster epoch advanced to {self._cluster_epoch} (Reason: {reason})."
                )
            return self._cluster_epoch

    def get_membership_changes(self) -> int:
        with self._lock:
            return self._membership_changes
