"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Query Engine

High-level descriptive query interface for Journey Maturity, Momentum, Stability,
Velocity, Residency, and Observed Probability metrics.
"""

from __future__ import annotations

from typing import List, Optional, Union
import uuid

from app.domain.journey.maturity.models import (
    JourneyHealth,
    JourneyHealthState,
    JourneyMaturityLevel,
    JourneyMaturityResult,
    JourneyMomentum,
    JourneyMomentumState,
    JourneyStability,
    JourneyStabilityLevel,
    ObservedJourneyProbability,
    StageResidency,
    StageVelocityState,
)
from app.domain.journey.maturity.repository import (
    JourneyMaturityReadRepository,
    default_maturity_repository,
)


class JourneyMaturityQueryEngine:
    """
    Read-only descriptive intelligence query engine for maturity artifacts.
    """

    def __init__(
        self,
        repository: Optional[JourneyMaturityReadRepository] = None,
    ) -> None:
        self._repo = repository or default_maturity_repository

    def get_maturity_result(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMaturityResult]:
        return self._repo.get_latest_maturity(journey_id)

    def get_maturity_score(self, journey_id: Union[uuid.UUID, str]) -> Optional[float]:
        result = self._repo.get_latest_maturity(journey_id)
        return result.maturity.maturity_score if result else None

    def get_maturity_level(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMaturityLevel]:
        result = self._repo.get_latest_maturity(journey_id)
        return result.maturity.maturity_level if result else None

    def get_momentum(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMomentum]:
        result = self._repo.get_latest_maturity(journey_id)
        return result.momentum if result else None

    def get_stability(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyStability]:
        result = self._repo.get_latest_maturity(journey_id)
        return result.stability if result else None

    def get_stage_residency(self, journey_id: Union[uuid.UUID, str]) -> List[StageResidency]:
        return self._repo.get_stage_residency(journey_id)

    def get_observed_probability(self, journey_id: Union[uuid.UUID, str]) -> Optional[ObservedJourneyProbability]:
        return self._repo.get_observed_probability(journey_id)

    def get_health(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyHealth]:
        result = self._repo.get_latest_maturity(journey_id)
        return result.health if result else None

    def get_journeys_by_maturity_level(
        self,
        workspace_id: Union[uuid.UUID, str],
        level: JourneyMaturityLevel,
    ) -> List[JourneyMaturityResult]:
        return self._repo.query_maturity(workspace_id=workspace_id, level=level)

    def get_stalled_journeys(
        self,
        workspace_id: Union[uuid.UUID, str],
    ) -> List[JourneyMaturityResult]:
        all_results = self._repo.query_maturity(workspace_id=workspace_id)
        return [
            r for r in all_results
            if r.velocity.velocity_state == StageVelocityState.STALLED or r.health.state == JourneyHealthState.STALLED
        ]

    def get_regressing_journeys(
        self,
        workspace_id: Union[uuid.UUID, str],
    ) -> List[JourneyMaturityResult]:
        all_results = self._repo.query_maturity(workspace_id=workspace_id)
        return [
            r for r in all_results
            if r.momentum.state == JourneyMomentumState.REGRESSING or r.stability.stability_level in (
                JourneyStabilityLevel.UNSTABLE,
                JourneyStabilityLevel.HIGHLY_UNSTABLE,
            )
        ]


default_maturity_query_engine = JourneyMaturityQueryEngine()
