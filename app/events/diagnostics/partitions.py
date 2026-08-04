"""
HunterOS Engage — Partition Diagnostics Collector
app/events/diagnostics/partitions.py

Passive operational diagnostics collector for active/waiting partitions,
backlog depths, hot partitions, and event aging.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import PartitionDetail, PartitionDiagnostics
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractPartitionDiagnosticsCollector(ABC):
    """
    Abstract interface for partition diagnostics collection.
    """

    @abstractmethod
    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> PartitionDiagnostics:
        """
        Collects point-in-time diagnostics for all monitored partitions.
        """
        pass


class DefaultPartitionDiagnosticsCollector(AbstractPartitionDiagnosticsCollector):
    """
    Production-grade passive partition diagnostics collector.
    Inspects partition states, backlog sizes, and lock states.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or DiagnosticsConfig()
        self._lock = threading.Lock()
        self._partitions: Dict[str, PartitionDetail] = {}

    def record_partition_state(
        self,
        partition_key: str,
        state: str = "ACTIVE",
        pending_events_count: int = 0,
        oldest_event_age_sec: Optional[float] = None,
        lock_owner: Optional[str] = None,
        lock_remaining_seconds: Optional[float] = None,
    ) -> None:
        """
        Thread-safe method to register or update partition state.
        """
        try:
            with self._lock:
                self._partitions[partition_key] = PartitionDetail(
                    partition_key=partition_key,
                    state=state,
                    pending_events_count=pending_events_count,
                    oldest_event_age_sec=oldest_event_age_sec,
                    lock_owner=lock_owner,
                    lock_remaining_seconds=lock_remaining_seconds,
                )
        except Exception as exc:
            logger.debug(f"[PartitionDiagnostics] Failed to record partition state: {exc}")

    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> PartitionDiagnostics:
        try:
            with self._lock:
                p_list = [p.model_copy() for p in self._partitions.values()]

            m_snap = event_metrics.snapshot()

            if not p_list:
                # Default baseline
                p_list = [
                    PartitionDetail(
                        partition_key="partition_default",
                        state="ACTIVE",
                        pending_events_count=m_snap.largest_partition or 0,
                        oldest_event_age_sec=0.0,
                    )
                ]

            total_partitions = len(p_list)
            active_count = sum(1 for p in p_list if p.state in ("ACTIVE", "PROCESSING")) or m_snap.active_partitions
            waiting_count = sum(1 for p in p_list if p.state == "WAITING") or m_snap.waiting_partitions
            total_backlog = sum(p.pending_events_count for p in p_list)

            # Sort for hottest partitions
            hottest = sorted(p_list, key=lambda p: p.pending_events_count, reverse=True)[:5]
            max_age = max((p.oldest_event_age_sec or 0.0 for p in p_list), default=0.0)

            return PartitionDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                total_partitions=total_partitions,
                active_partitions_count=active_count,
                waiting_partitions_count=waiting_count,
                total_partition_backlog=total_backlog,
                hottest_partitions=hottest,
                oldest_event_age_sec=round(max_age, 2),
                partition_throughput_per_sec=round(float(m_snap.events_processed), 2),
                partitions=p_list[: self.config.max_inspected_items],
            )
        except Exception as exc:
            logger.error(f"[PartitionDiagnostics] Error collecting partition diagnostics: {exc}", exc_info=True)
            return PartitionDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                total_partitions=1,
                active_partitions_count=1,
            )
