"""
HunterOS Engage V1 — Journey Analytics Engine
Phase 2.4.4: Analytics Execution Context

Read-only context holding all source data required for analytics pipeline.
Never mutates source data.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from app.domain.journey.models import JourneyState, JourneyStageTransition
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import AnalyticsObservationWindow, AnalyticsScope, JourneyCohortDefinition
from app.domain.journey.analytics.configuration import JourneyAnalyticsConfiguration

@dataclass(frozen=True)
class JourneyAnalyticsContext:
    workspace_id: Union[uuid.UUID, str]
    observation_window: AnalyticsObservationWindow
    journey_states: List[JourneyState]
    transitions: List[JourneyStageTransition]  # all transitions across all journeys
    maturity_results: List[JourneyMaturityResult]  # latest maturity per journey
    configuration: JourneyAnalyticsConfiguration  # from configuration.py
    journey_type: Optional[str] = None
    definition_version: Optional[str] = None
    cohort: Optional[JourneyCohortDefinition] = None
    scope: AnalyticsScope = AnalyticsScope.WORKSPACE
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def journey_count(self) -> int:
        return len(self.journey_states)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)

    @property
    def maturity_result_count(self) -> int:
        return len(self.maturity_results)

    def get_maturity_for_journey(self, journey_id: uuid.UUID) -> Optional[JourneyMaturityResult]:
        for mr in self.maturity_results:
            if mr.journey_id == journey_id:
                return mr
        return None

    def get_transitions_for_journey(self, journey_id: uuid.UUID) -> List[JourneyStageTransition]:
        jid = str(journey_id)
        return [t for t in self.transitions if str(t.journey_instance_id) == jid]
