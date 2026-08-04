"""
Interface-Driven Lease-Based Partition Lock Manager for HunterOS Engage.

Ensures that at most one worker processes an ORDERED partition at any time.

Design Principles:
    - Interface-driven: Defined by AbstractPartitionLockManager.
    - Lease-based: acquire_lock() returns a cryptographically unique lease_token.
      release_lock() requires the exact matching lease_token.
      A worker cannot release another worker's lock.
    - Safe auto-reclamation: Expired locks are safely reclaimed on acquisition.
    - Pluggable: InMemoryPartitionLockManager is the default. Distributed implementations
      (Redis/PostgreSQL) can be plugged in without changing dispatcher or worker code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import threading
from typing import Any, Dict, Optional
import uuid

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PartitionLockLease:
    """
    Represents an active partition lock lease.
    """
    partition_key: str
    lease_token: str
    acquired_at: datetime
    expires_at: datetime
    timeout_seconds: float

    @property
    def is_expired(self) -> bool:
        """Returns True if the lease has expired according to UTC clock."""
        return datetime.now(timezone.utc) >= self.expires_at


class AbstractPartitionLockManager(ABC):
    """
    Abstract interface for Partition Lock Managers.
    All components (Dispatcher, Worker, Reliability API) depend strictly on this interface.
    """

    @abstractmethod
    def acquire_lock(self, partition_key: str, timeout_seconds: float = 60.0) -> Optional[str]:
        """
        Attempts to acquire an exclusive lock on the partition.

        Args:
            partition_key: Unique partition identifier (e.g. 'conversation:123').
            timeout_seconds: Maximum lease duration before auto-expiration.

        Returns:
            Unique lease_token string if acquired, or None if currently locked.
        """
        pass

    @abstractmethod
    def release_lock(self, partition_key: str, lease_token: str) -> bool:
        """
        Releases the lock on a partition if the provided lease_token matches.

        Args:
            partition_key: Unique partition identifier.
            lease_token: The token received upon acquiring the lock.

        Returns:
            True if released, False if token mismatch or lock was not held.
        """
        pass

    @abstractmethod
    def force_release(self, partition_key: str) -> bool:
        """
        Forcefully clears any lock on the partition (used for administration or emergency recovery).

        Args:
            partition_key: Unique partition identifier.

        Returns:
            True if a lock was cleared, False otherwise.
        """
        pass

    @abstractmethod
    def is_locked(self, partition_key: str) -> bool:
        """
        Checks whether a partition is currently locked by an active, unexpired lease.

        Args:
            partition_key: Unique partition identifier.

        Returns:
            True if locked and not expired, False otherwise.
        """
        pass

    @abstractmethod
    def cleanup_expired_locks(self) -> int:
        """
        Purges expired locks.

        Returns:
            Count of expired locks purged.
        """
        pass

    @abstractmethod
    def get_active_locks(self) -> Dict[str, PartitionLockLease]:
        """
        Returns a snapshot of all currently active (unexpired) lock leases.
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Returns aggregated lock statistics for observability and monitoring.
        """
        pass


class InMemoryPartitionLockManager(AbstractPartitionLockManager):
    """
    Thread-safe, in-memory implementation of AbstractPartitionLockManager.
    Suitable for single-process workers, test suites, and default deployments.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._leases: Dict[str, PartitionLockLease] = {}
        # Metrics & Telemetry
        self._locks_acquired: int = 0
        self._locks_released: int = 0
        self._lock_conflicts: int = 0
        self._lock_timeouts: int = 0
        self._total_lock_duration_ms: float = 0.0

    def acquire_lock(self, partition_key: str, timeout_seconds: float = 60.0) -> Optional[str]:
        with self._lock:
            now = datetime.now(timezone.utc)
            existing = self._leases.get(partition_key)

            if existing:
                if not existing.is_expired:
                    # Active conflict
                    self._lock_conflicts += 1
                    logger.debug(
                        "partition_lock_conflict",
                        partition_key=partition_key,
                        expires_at=existing.expires_at.isoformat(),
                    )
                    return None
                else:
                    # Expired lease — reclaim safely
                    self._lock_timeouts += 1
                    logger.warning(
                        "partition_lock_expired_reclaimed",
                        partition_key=partition_key,
                        previous_token=existing.lease_token,
                        expired_at=existing.expires_at.isoformat(),
                    )

            # Create new lease
            lease_token = f"lease_{uuid.uuid4().hex}"
            expires_at = now + timedelta(seconds=max(0.001, timeout_seconds))
            lease = PartitionLockLease(
                partition_key=partition_key,
                lease_token=lease_token,
                acquired_at=now,
                expires_at=expires_at,
                timeout_seconds=timeout_seconds,
            )
            self._leases[partition_key] = lease
            self._locks_acquired += 1

            logger.debug(
                "partition_lock_acquired",
                partition_key=partition_key,
                lease_token=lease_token,
                timeout_seconds=timeout_seconds,
            )
            return lease_token

    def release_lock(self, partition_key: str, lease_token: str) -> bool:
        with self._lock:
            existing = self._leases.get(partition_key)
            if not existing:
                return False

            if existing.lease_token != lease_token:
                logger.warning(
                    "partition_lock_release_token_mismatch",
                    partition_key=partition_key,
                    provided_token=lease_token,
                    held_token=existing.lease_token,
                )
                return False

            now = datetime.now(timezone.utc)
            duration_ms = (now - existing.acquired_at).total_seconds() * 1000.0
            self._total_lock_duration_ms += max(0.0, duration_ms)
            self._locks_released += 1

            del self._leases[partition_key]

            logger.debug(
                "partition_lock_released",
                partition_key=partition_key,
                lease_token=lease_token,
                duration_ms=duration_ms,
            )
            return True

    def force_release(self, partition_key: str) -> bool:
        with self._lock:
            if partition_key in self._leases:
                del self._leases[partition_key]
                self._locks_released += 1
                logger.info("partition_lock_force_released", partition_key=partition_key)
                return True
            return False

    def is_locked(self, partition_key: str) -> bool:
        with self._lock:
            existing = self._leases.get(partition_key)
            if not existing:
                return False
            if existing.is_expired:
                # Lazy cleanup
                del self._leases[partition_key]
                self._lock_timeouts += 1
                return False
            return True

    def cleanup_expired_locks(self) -> int:
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [k for k, v in self._leases.items() if v.expires_at <= now]
            for k in expired_keys:
                del self._leases[k]
                self._lock_timeouts += 1
            if expired_keys:
                logger.info("partition_locks_expired_cleaned", count=len(expired_keys))
            return len(expired_keys)

    def get_active_locks(self) -> Dict[str, PartitionLockLease]:
        with self._lock:
            now = datetime.now(timezone.utc)
            # Filter out expired leases
            return {
                k: v for k, v in self._leases.items()
                if v.expires_at > now
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_count = len(self.get_active_locks())
            avg_duration = (
                self._total_lock_duration_ms / self._locks_released
                if self._locks_released > 0 else 0.0
            )
            return {
                "active_locks": active_count,
                "locks_acquired": self._locks_acquired,
                "locks_released": self._locks_released,
                "lock_conflicts": self._lock_conflicts,
                "lock_timeouts": self._lock_timeouts,
                "avg_lock_duration_ms": round(avg_duration, 2),
            }


# Global singleton management
_global_lock_manager: AbstractPartitionLockManager = InMemoryPartitionLockManager()


def get_lock_manager() -> AbstractPartitionLockManager:
    """Returns the globally configured PartitionLockManager instance."""
    global _global_lock_manager
    return _global_lock_manager


def set_lock_manager(manager: AbstractPartitionLockManager) -> None:
    """Configures a custom PartitionLockManager implementation (e.g. Redis, PostgreSQL)."""
    global _global_lock_manager
    if not isinstance(manager, AbstractPartitionLockManager):
        raise TypeError("manager must implement AbstractPartitionLockManager")
    _global_lock_manager = manager
