"""
Central Cluster Coordinator for HunterOS Distributed Dispatcher.
"""

import asyncio
from datetime import datetime, timezone
import os
import socket
from typing import Any, Dict, List, Optional

from app.events.cluster.config import ClusterConfig
from app.events.cluster.cluster_scheduler import (
    AbstractConsistentHashRing,
    ClusterDispatchCoordinator,
    DefaultConsistentHashRing,
    PartitionAssignmentPlan,
)
from app.events.cluster.heartbeat import HeartbeatManager
from app.events.cluster.leader import LeaderElectionEngine
from app.events.cluster.lease import AbstractDispatcherLeaseManager, InMemoryDispatcherLeaseManager
from app.events.cluster.registry import (
    AbstractDispatcherRegistry,
    DispatcherNode,
    DispatcherStatus,
    InMemoryDispatcherRegistry,
)
from app.events.store.models import EventRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ClusterCoordinator:
    """
    Coordinates distributed dispatcher operations across a cluster of nodes.
    Integrates membership registry, lease management, leader election, heartbeats,
    and interface-driven consistent hash ring partition scheduling.
    """

    def __init__(
        self,
        dispatcher_id: Optional[str] = None,
        registry: Optional[AbstractDispatcherRegistry] = None,
        lease_manager: Optional[AbstractDispatcherLeaseManager] = None,
        ring: Optional[AbstractConsistentHashRing] = None,
        config: Optional[ClusterConfig] = None,
    ):
        self.config = config or ClusterConfig.from_env()
        self.dispatcher_id = dispatcher_id or f"dispatcher-{os.getpid()}-{socket.gethostname()}"
        self.registry = registry or InMemoryDispatcherRegistry()
        self.lease_manager = lease_manager or InMemoryDispatcherLeaseManager()
        self.leader_engine = LeaderElectionEngine(
            dispatcher_id=self.dispatcher_id,
            registry=self.registry,
            lease_manager=self.lease_manager,
            config=self.config,
        )
        self.heartbeat_manager = HeartbeatManager(
            dispatcher_id=self.dispatcher_id,
            registry=self.registry,
            leader_engine=self.leader_engine,
            config=self.config,
        )
        self.scheduler = ClusterDispatchCoordinator(
            ring=ring,
            config=self.config,
        )
        self.startup_timestamp = datetime.now(timezone.utc)

    def start(self) -> None:
        """
        Registers the local dispatcher node into the cluster and attempts leadership election.
        """
        hostname = socket.gethostname()
        pid = os.getpid()

        node = DispatcherNode(
            dispatcher_id=self.dispatcher_id,
            hostname=hostname,
            pid=pid,
            startup_timestamp=self.startup_timestamp,
            version="1.0.0",
            status=DispatcherStatus.ACTIVE,
            is_leader=False,
            active_dispatch_count=0,
        )

        epoch = self.registry.register(node)
        self.leader_engine.attempt_election()
        self.heartbeat_manager.execute_heartbeat_cycle()

        logger.info(
            f"ClusterCoordinator started for node '{self.dispatcher_id}' "
            f"(Epoch: {epoch}, Leader: {self.leader_engine.is_leader()})"
        )

    async def stop(self) -> None:
        """
        Gracefully stops heartbeat broadcasting, releases leadership lease if held,
        and unregisters the node from the cluster.
        """
        logger.info(f"Stopping ClusterCoordinator for node '{self.dispatcher_id}'...")
        await self.heartbeat_manager.stop()

        if self.leader_engine.is_leader():
            self.leader_engine.step_down()

        self.registry.unregister(self.dispatcher_id)

    def plan_local_assignments(
        self,
        candidate_records: List[EventRecord],
        now: Optional[datetime] = None,
    ) -> PartitionAssignmentPlan:
        """
        Plans deterministic partition ownership for candidate records using the consistent hash ring.
        Returns a PartitionAssignmentPlan containing only the events assigned to this local node.
        """
        healthy_nodes = self.registry.get_healthy_nodes(
            timeout_seconds=self.config.node_timeout_seconds,
            now=now,
        )
        healthy_ids = [n.dispatcher_id for n in healthy_nodes]
        epoch = self.registry.get_current_epoch()

        return self.scheduler.plan_local_assignments(
            candidate_records=candidate_records,
            local_dispatcher_id=self.dispatcher_id,
            healthy_nodes=healthy_ids,
            cluster_epoch=epoch,
        )

    def is_leader(self, now: Optional[datetime] = None) -> bool:
        """Returns True if this local dispatcher is the active cluster leader."""
        return self.leader_engine.is_leader(now=now)

    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Returns structured cluster status for the Reliability API.
        """
        healthy_nodes = self.registry.get_healthy_nodes(self.config.node_timeout_seconds)
        all_nodes = self.registry.get_cluster()
        leader_id = self.leader_engine.get_current_leader_id()
        current_lease = self.lease_manager.get_current_leader()

        total = len(all_nodes)
        healthy = len(healthy_nodes)
        health_score = 100 if total == 0 else int((healthy / total) * 100)
        if not leader_id:
            health_score = max(0, health_score - 20)

        uptime_seconds = (datetime.now(timezone.utc) - self.startup_timestamp).total_seconds()

        return {
            "cluster_version": "1.0.0",
            "cluster_epoch": self.registry.get_current_epoch(),
            "ring_version": self.scheduler.ring.get_ring_version(),
            "membership_changes": self.registry.get_membership_changes(),
            "health_score": health_score,
            "cluster_uptime_seconds": uptime_seconds,
            "leader": {
                "leader_id": leader_id,
                "is_current_node": (leader_id == self.dispatcher_id),
                "lease_token_prefix": current_lease.lease_token[:8] if current_lease else None,
                "expires_at": current_lease.expires_at.isoformat() if current_lease else None,
                "renew_count": current_lease.renew_count if current_lease else 0,
            },
            "nodes": [n.to_dict() for n in all_nodes],
            "healthy_node_count": healthy,
            "total_node_count": total,
        }


# Global singleton cluster coordinator instance
default_cluster_coordinator = ClusterCoordinator()

