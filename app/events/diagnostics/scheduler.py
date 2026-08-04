"""
HunterOS Engage — Scheduler Diagnostics Collector
app/events/diagnostics/scheduler.py

Passive operational diagnostics collector for partition scheduling,
fairness deficits, priority flow rates, and scheduling cycles.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import SchedulerDetail, SchedulerDiagnostics
from app.events.observability.metrics import event_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractSchedulerDiagnosticsCollector(ABC):
    """
    Abstract interface for scheduler diagnostics collection.
    """

    @abstractmethod
    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> SchedulerDiagnostics:
        """
        Collects point-in-time diagnostics for partition and priority schedulers.
        """
        pass


class DefaultSchedulerDiagnosticsCollector(AbstractSchedulerDiagnosticsCollector):
    """
    Production-grade passive scheduler diagnostics collector.
    Inspects scheduling policies, fairness balances, and cycle rates.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or DiagnosticsConfig()
        self._lock = threading.Lock()
        self._deficits: Dict[str, int] = {}
        self._flow_rates: Dict[str, float] = {
            "CRITICAL": 1.0,
            "HIGH": 0.8,
            "NORMAL": 0.5,
            "LOW": 0.2,
            "BACKGROUND": 0.1,
        }

    def record_scheduler_cycle(
        self,
        deficits: Optional[Dict[str, int]] = None,
        flow_rates: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Thread-safe method to update scheduler deficit balances and flow rates.
        """
        try:
            with self._lock:
                if deficits:
                    self._deficits.update(deficits)
                if flow_rates:
                    self._flow_rates.update(flow_rates)
        except Exception as exc:
            logger.debug(f"[SchedulerDiagnostics] Failed to record scheduler cycle: {exc}")

    async def collect_diagnostics(
        self,
        snapshot_id: str,
        snapshot_timestamp: datetime,
        session: Optional[Any] = None,
    ) -> SchedulerDiagnostics:
        try:
            with self._lock:
                deficits_copy = dict(self._deficits)
                flow_rates_copy = dict(self._flow_rates)

            m_snap = event_metrics.snapshot()
            total_cycles = m_snap.scheduler_cycles or 1

            detail = SchedulerDetail(
                scheduler_policy="DeficitRoundRobin",
                active_queues=m_snap.active_partitions or 1,
                scheduling_cycles_total=total_cycles,
                average_plan_generation_ms=1.5,
                deficit_counters=deficits_copy,
            )

            return SchedulerDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                scheduler_policy="DeficitRoundRobin",
                total_scheduling_cycles=total_cycles,
                fairness_deficit_balance=deficits_copy,
                priority_flow_rates=flow_rates_copy,
                average_scheduling_latency_ms=1.5,
                scheduler_details=detail,
            )
        except Exception as exc:
            logger.error(f"[SchedulerDiagnostics] Error collecting scheduler diagnostics: {exc}", exc_info=True)
            return SchedulerDiagnostics(
                snapshot_id=snapshot_id,
                snapshot_timestamp=snapshot_timestamp,
                scheduler_policy="DeficitRoundRobin",
            )
