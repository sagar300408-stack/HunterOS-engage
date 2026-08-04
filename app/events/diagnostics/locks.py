"""
HunterOS Engage — Lock Diagnostics Collector
app/events/diagnostics/locks.py

Passive operational diagnostics collector for active partition locks,
lease durations, expired locks, ownership distribution, and lock contention.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import LockDetail, LockDiagnostics
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractLockDiagnosticsCollector(ABC):
    """
    Abstract interface for lock diagnostics collection.
    """

    @abstractmethod
    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> LockDiagnostics:
        """
        Collects point-in-time diagnostics for active and expired locks.
        """
        pass


class DefaultLockDiagnosticsCollector(AbstractLockDiagnosticsCollector):
    """
    Production-grade passive lock diagnostics collector.
    Inspects lock leases, expiration states, and contention rates.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or DiagnosticsConfig()
        self._lock = threading.Lock()
        self._locks: Dict[str, LockDetail] = {}

    def record_lock_lease(
        self,
        resource_id: str,
        owner_id: str,
        expires_at: Optional[datetime] = None,
        remaining_lease_sec: float = 30.0,
    ) -> None:
        """
        Thread-safe method to register or update an active lock lease.
        """
        try:
            with self._lock:
                now = datetime.now(timezone.utc)
                self._locks[resource_id] = LockDetail(
                    resource_id=resource_id,
                    owner_id=owner_id,
                    acquired_at=now,
                    expires_at=expires_at,
                    remaining_lease_sec=remaining_lease_sec,
                    is_expired=False,
                )
        except Exception as exc:
            logger.debug(f"[LockDiagnostics] Failed to record lock lease: {exc}")

    def release_lock(self, resource_id: str) -> None:
        """
        Thread-safe method to remove a released lock.
        """
        try:
            with self._lock:
                self._locks.pop(resource_id, None)
        except Exception as exc:
            logger.debug(f"[LockDiagnostics] Failed to release lock record: {exc}")

    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> LockDiagnostics:
        try:
            now = snapshot_timestamp
            with self._lock:
                lock_list: List[LockDetail] = []
                for res_id, l in list(self._locks.items()):
                    if l.expires_at and l.expires_at < now:
                        l.is_expired = True
                        l.remaining_lease_sec = 0.0
                    elif l.expires_at:
                        l.remaining_lease_sec = max(0.0, (l.expires_at - now).total_seconds())
                        l.is_expired = False
                    lock_list.append(l.model_copy())

            active_locks_count = sum(1 for l in lock_list if not l.is_expired)
            expired_locks_count = sum(1 for l in lock_list if l.is_expired)

            owners_map: Dict[str, int] = {}
            for l in lock_list:
                if not l.is_expired:
                    owners_map[l.owner_id] = owners_map.get(l.owner_id, 0) + 1

            durations = [l.remaining_lease_sec for l in lock_list if not l.is_expired]
            avg_lease = sum(durations) / len(durations) if durations else 0.0

            m_snap = event_metrics.snapshot()
            contention = m_snap.partition_lock_conflicts

            return LockDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                active_locks_count=active_locks_count,
                expired_locks_count=expired_locks_count,
                lock_owners=owners_map,
                average_lease_duration_sec=round(avg_lease, 2),
                lock_contention_events_total=contention,
                locks=lock_list[: self.config.max_inspected_items],
            )
        except Exception as exc:
            logger.error(f"[LockDiagnostics] Error collecting lock diagnostics: {exc}", exc_info=True)
            return LockDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                active_locks_count=0,
                expired_locks_count=0,
            )
