"""
Heartbeat & Cluster Health Monitoring Engine for HunterOS Distributed Dispatcher.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional

from app.events.cluster.config import ClusterConfig
from app.events.cluster.leader import LeaderElectionEngine
from app.events.cluster.registry import AbstractDispatcherRegistry
from app.events.observability.metrics import event_metrics

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Manages node heartbeat broadcasting and cluster-wide dead node maintenance.
    """

    def __init__(
        self,
        dispatcher_id: str,
        registry: AbstractDispatcherRegistry,
        leader_engine: LeaderElectionEngine,
        config: Optional[ClusterConfig] = None,
    ):
        self.dispatcher_id = dispatcher_id
        self.registry = registry
        self.leader_engine = leader_engine
        self.config = config or ClusterConfig()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    def execute_heartbeat_cycle(
        self,
        active_dispatch_count: int = 0,
        now: Optional[datetime] = None,
    ) -> None:
        """
        Executes a single heartbeat cycle:
        1. Emits local heartbeat to registry.
        2. If leader, runs cluster health maintenance and dead node pruning.
        3. Updates cluster-level metrics.
        """
        current_time = now or datetime.now(timezone.utc)

        # 1. Emit local node heartbeat
        self.registry.heartbeat(
            dispatcher_id=self.dispatcher_id,
            active_dispatch_count=active_dispatch_count,
            now=current_time,
        )
        try:
            event_metrics.increment("dispatcher_heartbeats")
        except KeyError:
            pass

        # 2. Leader-only maintenance duties
        is_leader = self.leader_engine.is_leader(now=current_time)
        if is_leader:
            pruned = self.registry.prune_dead_nodes(
                timeout_seconds=self.config.node_timeout_seconds,
                now=current_time,
            )
            if pruned:
                try:
                    event_metrics.increment("dispatcher_failures", len(pruned))
                except KeyError:
                    pass

        # 3. Update Cluster Gauges
        healthy_nodes = self.registry.get_healthy_nodes(
            timeout_seconds=self.config.node_timeout_seconds,
            now=current_time,
        )
        all_nodes = self.registry.get_cluster()
        total_count = len(all_nodes)
        healthy_count = len(healthy_nodes)

        # Health score calculation (0 to 100)
        if total_count == 0:
            health_score = 100
        else:
            health_score = int((healthy_count / total_count) * 100)
            if not self.leader_engine.get_current_leader_id(now=current_time):
                health_score = max(0, health_score - 20)  # Penalize leaderless state

        try:
            event_metrics.set("cluster_nodes", total_count)
            event_metrics.set("healthy_nodes", healthy_count)
            event_metrics.set("cluster_epoch", self.registry.get_current_epoch())
            event_metrics.set("cluster_health_score", health_score)
            event_metrics.set("membership_changes", self.registry.get_membership_changes())
        except KeyError:
            pass

    async def run(self):
        """Asynchronous background loop for periodic heartbeat and cluster maintenance."""
        logger.info(
            f"Starting HeartbeatManager for dispatcher [{self.dispatcher_id}] "
            f"(Interval: {self.config.heartbeat_interval_seconds}s)"
        )
        while not self._stop_event.is_set():
            try:
                # Attempt leader election or renewal
                self.leader_engine.attempt_election()
                # Run heartbeat cycle
                self.execute_heartbeat_cycle()
            except Exception as e:
                logger.error(f"Error in HeartbeatManager loop: {e}", exc_info=True)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.heartbeat_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    def start(self):
        """Starts the heartbeat manager task in the current event loop."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self.run())

    async def stop(self):
        """Signals the heartbeat manager to stop gracefully."""
        self._stop_event.set()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
