"""
HunterOS Distributed Dispatcher Cluster Coordination Package.
"""

from app.events.cluster.config import ClusterConfig
from app.events.cluster.cluster_scheduler import (
    AbstractConsistentHashRing,
    ClusterDispatchCoordinator,
    DefaultConsistentHashRing,
    PartitionAssignmentPlan,
)
from app.events.cluster.coordinator import ClusterCoordinator, default_cluster_coordinator
from app.events.cluster.heartbeat import HeartbeatManager
from app.events.cluster.leader import LeaderElectionEngine
from app.events.cluster.lease import (
    AbstractDispatcherLeaseManager,
    InMemoryDispatcherLeaseManager,
    LeaderLease,
)
from app.events.cluster.registry import (
    AbstractDispatcherRegistry,
    DispatcherNode,
    DispatcherStatus,
    InMemoryDispatcherRegistry,
)
from app.events.cluster.validator import ClusterStartupValidator

__all__ = [
    "ClusterConfig",
    "AbstractConsistentHashRing",
    "DefaultConsistentHashRing",
    "PartitionAssignmentPlan",
    "ClusterDispatchCoordinator",
    "ClusterCoordinator",
    "default_cluster_coordinator",
    "HeartbeatManager",
    "LeaderElectionEngine",
    "AbstractDispatcherLeaseManager",
    "InMemoryDispatcherLeaseManager",
    "LeaderLease",
    "AbstractDispatcherRegistry",
    "DispatcherNode",
    "DispatcherStatus",
    "InMemoryDispatcherRegistry",
    "ClusterStartupValidator",
]
