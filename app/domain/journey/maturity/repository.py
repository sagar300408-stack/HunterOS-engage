"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity CQRS Repositories

Abstract read/write repositories and thread-safe InMemory implementation
for storing and querying immutable JourneyMaturityResults.
"""

from __future__ import annotations

import abc
import threading
from typing import Dict, List, Optional, Union
import uuid

from app.domain.journey.maturity.models import (
    JourneyMaturityLevel,
    JourneyMaturityResult,
    JourneyMomentum,
    JourneyStability,
    ObservedJourneyProbability,
    StageResidency,
)


class JourneyMaturityReadRepository(abc.ABC):
    """Abstract read repository for journey maturity data."""

    @abc.abstractmethod
    def get_latest_maturity(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMaturityResult]:
        pass

    @abc.abstractmethod
    def get_maturity_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyMaturityResult]:
        pass

    @abc.abstractmethod
    def query_maturity(
        self,
        workspace_id: Union[uuid.UUID, str],
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        level: Optional[JourneyMaturityLevel] = None,
    ) -> List[JourneyMaturityResult]:
        pass

    @abc.abstractmethod
    def get_observed_probability(self, journey_id: Union[uuid.UUID, str]) -> Optional[ObservedJourneyProbability]:
        pass

    @abc.abstractmethod
    def get_stage_residency(self, journey_id: Union[uuid.UUID, str]) -> List[StageResidency]:
        pass

    @abc.abstractmethod
    def get_momentum_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyMomentum]:
        pass

    @abc.abstractmethod
    def get_stability_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyStability]:
        pass


class JourneyMaturityWriteRepository(abc.ABC):
    """Abstract write repository for saving immutable journey maturity results."""

    @abc.abstractmethod
    def save_maturity_result(self, result: JourneyMaturityResult) -> None:
        pass


class InMemoryJourneyMaturityRepository(JourneyMaturityReadRepository, JourneyMaturityWriteRepository):
    """Thread-safe in-memory CQRS implementation for Journey Maturity storage."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._results_by_journey: Dict[str, List[JourneyMaturityResult]] = {}
        self._results_by_workspace: Dict[str, List[JourneyMaturityResult]] = {}

    def _j_key(self, journey_id: Union[uuid.UUID, str]) -> str:
        return str(journey_id)

    def _ws_key(self, workspace_id: Union[uuid.UUID, str]) -> str:
        return str(workspace_id)

    def save_maturity_result(self, result: JourneyMaturityResult) -> None:
        with self._lock:
            j_key = self._j_key(result.journey_id)
            ws_key = self._ws_key(result.workspace_id)

            if j_key not in self._results_by_journey:
                self._results_by_journey[j_key] = []
            self._results_by_journey[j_key].append(result)

            if ws_key not in self._results_by_workspace:
                self._results_by_workspace[ws_key] = []
            self._results_by_workspace[ws_key].append(result)

    def get_latest_maturity(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMaturityResult]:
        with self._lock:
            history = self._results_by_journey.get(self._j_key(journey_id), [])
            return history[-1] if history else None

    def get_maturity_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyMaturityResult]:
        with self._lock:
            return list(self._results_by_journey.get(self._j_key(journey_id), []))

    def query_maturity(
        self,
        workspace_id: Union[uuid.UUID, str],
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        level: Optional[JourneyMaturityLevel] = None,
    ) -> List[JourneyMaturityResult]:
        with self._lock:
            all_ws = self._results_by_workspace.get(self._ws_key(workspace_id), [])
            # Only consider the latest result for each journey
            latest_by_journey: Dict[str, JourneyMaturityResult] = {}
            for r in all_ws:
                latest_by_journey[str(r.journey_id)] = r

            filtered = []
            for r in latest_by_journey.values():
                score = r.maturity.maturity_score
                if min_score is not None and score < min_score:
                    continue
                if max_score is not None and score > max_score:
                    continue
                if level is not None and r.maturity.maturity_level != level:
                    continue
                filtered.append(r)
            return filtered

    def get_observed_probability(self, journey_id: Union[uuid.UUID, str]) -> Optional[ObservedJourneyProbability]:
        latest = self.get_latest_maturity(journey_id)
        return latest.observed_probability if latest else None

    def get_stage_residency(self, journey_id: Union[uuid.UUID, str]) -> List[StageResidency]:
        latest = self.get_latest_maturity(journey_id)
        return list(latest.stage_residency) if latest else []

    def get_momentum_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyMomentum]:
        history = self.get_maturity_history(journey_id)
        return [r.momentum for r in history]

    def get_stability_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyStability]:
        history = self.get_maturity_history(journey_id)
        return [r.stability for r in history]


default_maturity_repository = InMemoryJourneyMaturityRepository()
