"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Analytics CQRS Repositories

CQRS: Separate read and write sides. InMemory implementation for dev/test.
"""
from __future__ import annotations

import abc
import threading
from datetime import datetime
from typing import Dict, List, Optional, Union
import uuid

from app.domain.journey.analytics.models import (
    JourneyAnalyticsResult,
    AnalyticsObservationWindow,
)


class JourneyAnalyticsReadRepository(abc.ABC):
    @abc.abstractmethod
    def get_result(self, analytics_id: Union[uuid.UUID, str]) -> Optional[JourneyAnalyticsResult]: ...

    @abc.abstractmethod
    def get_latest_result(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyAnalyticsResult]: ...

    @abc.abstractmethod
    def query_results(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[JourneyAnalyticsResult]: ...


class JourneyAnalyticsWriteRepository(abc.ABC):
    @abc.abstractmethod
    def save_result(self, result: JourneyAnalyticsResult) -> None: ...


class InMemoryJourneyAnalyticsRepository(
    JourneyAnalyticsReadRepository, JourneyAnalyticsWriteRepository
):
    """Thread-safe in-memory CQRS implementation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._results: Dict[str, JourneyAnalyticsResult] = {}  # analytics_id -> result
        self._by_workspace: Dict[str, List[str]] = {}  # workspace_id -> [analytics_ids]

    def save_result(self, result: JourneyAnalyticsResult) -> None:
        with self._lock:
            aid = str(result.analytics_id)
            ws = str(result.workspace_id)
            self._results[aid] = result
            if ws not in self._by_workspace:
                self._by_workspace[ws] = []
            self._by_workspace[ws].append(aid)

    def get_result(self, analytics_id: Union[uuid.UUID, str]) -> Optional[JourneyAnalyticsResult]:
        with self._lock:
            return self._results.get(str(analytics_id))

    def get_latest_result(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyAnalyticsResult]:
        with self._lock:
            ws = str(workspace_id)
            ids = self._by_workspace.get(ws, [])
            # Filter and find latest
            candidates = [
                self._results[aid] for aid in ids if aid in self._results
            ]
            if journey_type:
                candidates = [r for r in candidates if r.journey_type == journey_type]
            if not candidates:
                return None
            return max(candidates, key=lambda r: r.generated_at)

    def query_results(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[JourneyAnalyticsResult]:
        with self._lock:
            ws = str(workspace_id)
            ids = self._by_workspace.get(ws, [])
            results = [self._results[aid] for aid in ids if aid in self._results]
            if journey_type:
                results = [r for r in results if r.journey_type == journey_type]
            if from_date:
                results = [r for r in results if r.generated_at >= from_date]
            if to_date:
                results = [r for r in results if r.generated_at <= to_date]
            return sorted(results, key=lambda r: r.generated_at)


default_analytics_repository: InMemoryJourneyAnalyticsRepository = InMemoryJourneyAnalyticsRepository()
