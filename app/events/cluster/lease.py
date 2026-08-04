"""
Distributed Lease Management for Cluster Leadership in HunterOS Engage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import threading
from typing import Optional
import uuid

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LeaderLease:
    """
    Immutable representation of an active leader lease.
    """
    leader_id: str
    lease_token: str
    acquired_at: datetime
    expires_at: datetime
    renew_count: int = 0
    version: int = 1

    @property
    def is_expired(self) -> bool:
        """Returns True if the lease has expired according to UTC clock."""
        return datetime.now(timezone.utc) >= self.expires_at

    def is_valid_at(self, now: datetime) -> bool:
        """Returns True if valid at the specified point in time."""
        return now < self.expires_at


class AbstractDispatcherLeaseManager(ABC):
    """
    Abstract interface for Dispatcher Cluster Leadership Lease Management.
    Enables pluggable backends (in-memory, Redis Redlock, PostgreSQL advisory locks, etcd).
    """

    @abstractmethod
    def acquire_leadership(
        self,
        dispatcher_id: str,
        lease_seconds: float = 10.0,
        now: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Attempts to acquire cluster leadership lease.
        Returns unique lease_token if acquired, or None if already held by an unexpired leader.
        """
        pass

    @abstractmethod
    def renew_leadership(
        self,
        dispatcher_id: str,
        lease_token: str,
        lease_seconds: float = 10.0,
        now: Optional[datetime] = None,
    ) -> bool:
        """
        Renews an existing leadership lease.
        Returns True if renewed, False if token mismatch or lease expired.
        """
        pass

    @abstractmethod
    def release_leadership(
        self,
        dispatcher_id: str,
        lease_token: str,
    ) -> bool:
        """
        Releases leadership lease if the provided lease_token matches.
        Returns True if successfully released, False otherwise.
        """
        pass

    @abstractmethod
    def get_current_leader(
        self, now: Optional[datetime] = None
    ) -> Optional[LeaderLease]:
        """Returns the active, unexpired LeaderLease, or None."""
        pass

    @abstractmethod
    def is_leader(
        self, dispatcher_id: str, now: Optional[datetime] = None
    ) -> bool:
        """Checks whether the specified dispatcher currently holds an active leadership lease."""
        pass

    @abstractmethod
    def force_revoke(self) -> bool:
        """Forcefully clears the leadership lease (for administrative recovery)."""
        pass


class InMemoryDispatcherLeaseManager(AbstractDispatcherLeaseManager):
    """
    Thread-safe in-memory implementation of lease manager with atomic lease token validation.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._current_lease: Optional[LeaderLease] = None
        self._lease_version_counter: int = 0

    def acquire_leadership(
        self,
        dispatcher_id: str,
        lease_seconds: float = 10.0,
        now: Optional[datetime] = None,
    ) -> Optional[str]:
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            # 1. If currently held and unexpired by another dispatcher, acquisition fails
            if self._current_lease is not None and self._current_lease.is_valid_at(current_time):
                if self._current_lease.leader_id == dispatcher_id:
                    # Current node already holds the valid lease; return existing token
                    return self._current_lease.lease_token
                return None

            # 2. Acquire or safely reclaim expired leadership
            self._lease_version_counter += 1
            new_token = uuid.uuid4().hex
            self._current_lease = LeaderLease(
                leader_id=dispatcher_id,
                lease_token=new_token,
                acquired_at=current_time,
                expires_at=current_time + timedelta(seconds=lease_seconds),
                renew_count=0,
                version=self._lease_version_counter,
            )
            logger.info(
                f"Leadership acquired by '{dispatcher_id}' (Token: {new_token[:8]}..., "
                f"TTL: {lease_seconds}s, Version: {self._lease_version_counter})"
            )
            return new_token

    def renew_leadership(
        self,
        dispatcher_id: str,
        lease_token: str,
        lease_seconds: float = 10.0,
        now: Optional[datetime] = None,
    ) -> bool:
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            if self._current_lease is None:
                return False

            # Strict verification of leader_id and lease_token
            if (
                self._current_lease.leader_id != dispatcher_id
                or self._current_lease.lease_token != lease_token
            ):
                return False

            # If already expired according to clock, renewal is rejected to prevent split-brain
            if not self._current_lease.is_valid_at(current_time):
                return False

            self._current_lease = LeaderLease(
                leader_id=dispatcher_id,
                lease_token=lease_token,
                acquired_at=self._current_lease.acquired_at,
                expires_at=current_time + timedelta(seconds=lease_seconds),
                renew_count=self._current_lease.renew_count + 1,
                version=self._current_lease.version,
            )
            return True

    def release_leadership(
        self,
        dispatcher_id: str,
        lease_token: str,
    ) -> bool:
        with self._lock:
            if self._current_lease is None:
                return False

            if (
                self._current_lease.leader_id == dispatcher_id
                and self._current_lease.lease_token == lease_token
            ):
                logger.info(f"Leadership released by '{dispatcher_id}'.")
                self._current_lease = None
                return True
            return False

    def get_current_leader(
        self, now: Optional[datetime] = None
    ) -> Optional[LeaderLease]:
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            if self._current_lease is None:
                return None
            if self._current_lease.is_valid_at(current_time):
                return self._current_lease
            return None

    def is_leader(
        self, dispatcher_id: str, now: Optional[datetime] = None
    ) -> bool:
        current_time = now or datetime.now(timezone.utc)
        with self._lock:
            if self._current_lease is None:
                return False
            return (
                self._current_lease.leader_id == dispatcher_id
                and self._current_lease.is_valid_at(current_time)
            )

    def force_revoke(self) -> bool:
        with self._lock:
            if self._current_lease is not None:
                logger.warning(
                    f"Leadership lease forcefully revoked (Previous leader: {self._current_lease.leader_id})."
                )
                self._current_lease = None
                return True
            return False
