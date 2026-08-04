"""
Leader Election Engine for HunterOS Distributed Dispatcher Cluster.
"""

from datetime import datetime, timezone
import threading
from typing import Optional

from app.events.cluster.config import ClusterConfig
from app.events.cluster.lease import AbstractDispatcherLeaseManager, InMemoryDispatcherLeaseManager
from app.events.cluster.registry import AbstractDispatcherRegistry
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LeaderElectionEngine:
    """
    Manages the leadership lifecycle for an individual dispatcher node.
    Coordinates lease acquisition, renewals, step-downs, and observability metrics.
    """

    def __init__(
        self,
        dispatcher_id: str,
        registry: AbstractDispatcherRegistry,
        lease_manager: Optional[AbstractDispatcherLeaseManager] = None,
        config: Optional[ClusterConfig] = None,
    ):
        self.dispatcher_id = dispatcher_id
        self.registry = registry
        self.lease_manager = lease_manager or InMemoryDispatcherLeaseManager()
        self.config = config or ClusterConfig()
        self._lock = threading.RLock()
        self._lease_token: Optional[str] = None
        self._last_elected_leader: Optional[str] = None

    @property
    def lease_token(self) -> Optional[str]:
        with self._lock:
            return self._lease_token

    def attempt_election(self, now: Optional[datetime] = None) -> bool:
        """
        Attempts to acquire cluster leadership or renew an existing lease.
        Returns True if this node is currently the active leader.
        """
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            # 1. If we already hold leadership, attempt renewal
            if self._lease_token is not None:
                renewed = self.renew_lease(now=current_time)
                if renewed:
                    return True

            # 2. Attempt acquiring a new lease
            token = self.lease_manager.acquire_leadership(
                dispatcher_id=self.dispatcher_id,
                lease_seconds=self.config.leader_lease_seconds,
                now=current_time,
            )

            if token is not None:
                was_not_leader = self._lease_token is None
                self._lease_token = token
                self._last_elected_leader = self.dispatcher_id

                if was_not_leader:
                    self.registry.increment_epoch(f"leader_elected:{self.dispatcher_id}")
                    try:
                        event_metrics.increment("leadership_acquisitions")
                        event_metrics.increment("leader_changes")
                    except KeyError:
                        pass
                    logger.info(
                        f"Dispatcher node '{self.dispatcher_id}' elected as cluster leader. "
                        f"(Lease TTL: {self.config.leader_lease_seconds}s)"
                    )
                return True
            else:
                # Leadership held by another or expired
                current_leader = self.lease_manager.get_current_leader(now=current_time)
                current_leader_id = current_leader.leader_id if current_leader else None

                if self._last_elected_leader != current_leader_id and current_leader_id is not None:
                    self._last_elected_leader = current_leader_id
                    try:
                        event_metrics.increment("leader_changes")
                    except KeyError:
                        pass

                if self._lease_token is not None:
                    self._lease_token = None
                    try:
                        event_metrics.increment("leadership_losses")
                    except KeyError:
                        pass
                    self.registry.increment_epoch(f"leadership_lost:{self.dispatcher_id}")
                    logger.warning(
                        f"Dispatcher node '{self.dispatcher_id}' lost cluster leadership."
                    )
                return False

    def renew_lease(self, now: Optional[datetime] = None) -> bool:
        """
        Renews an existing leadership lease.
        """
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            if not self._lease_token:
                return False

            success = self.lease_manager.renew_leadership(
                dispatcher_id=self.dispatcher_id,
                lease_token=self._lease_token,
                lease_seconds=self.config.leader_lease_seconds,
                now=current_time,
            )

            if not success:
                self._lease_token = None
                try:
                    event_metrics.increment("leadership_losses")
                except KeyError:
                    pass
                self.registry.increment_epoch(f"leadership_renewal_failed:{self.dispatcher_id}")
                logger.warning(
                    f"Leadership renewal failed for dispatcher '{self.dispatcher_id}'."
                )
                return False

            return True

    def step_down(self) -> bool:
        """
        Gracefully steps down from leadership and releases the lease token.
        """
        with self._lock:
            if not self._lease_token:
                return False

            released = self.lease_manager.release_leadership(
                dispatcher_id=self.dispatcher_id,
                lease_token=self._lease_token,
            )
            self._lease_token = None
            if released:
                self.registry.increment_epoch(f"leader_stepped_down:{self.dispatcher_id}")
                try:
                    event_metrics.increment("leadership_losses")
                except KeyError:
                    pass
                logger.info(
                    f"Dispatcher node '{self.dispatcher_id}' stepped down from cluster leadership."
                )
            return released

    def is_leader(self, now: Optional[datetime] = None) -> bool:
        """Returns True if this node holds the valid unexpired leadership lease."""
        current_time = now or datetime.now(timezone.utc)
        return self.lease_manager.is_leader(self.dispatcher_id, now=current_time)

    def get_current_leader_id(self, now: Optional[datetime] = None) -> Optional[str]:
        """Returns the dispatcher_id of the current unexpired cluster leader."""
        current_time = now or datetime.now(timezone.utc)
        lease = self.lease_manager.get_current_leader(now=current_time)
        return lease.leader_id if lease else None
