from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from app.domain.journey.repository import JourneyReadRepository, default_journey_repository
from app.domain.journey.models import (
    JourneyState,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyTimeline,
    JourneyStatus
)

class JourneyQueryEngine:
    """Engine for descriptive analytics and querying of journey data."""
    
    def __init__(self, repository: JourneyReadRepository):
        self._repository = repository

    def get_current_journey_state(self, journey_instance_id: str) -> Optional[JourneyState]:
        return self._repository.get_journey(journey_instance_id)

    def get_stage_history(self, journey_instance_id: str) -> List[JourneyStageCode]:
        return self._repository.get_stage_history(journey_instance_id)

    def get_transition_history(self, journey_instance_id: str) -> List[JourneyStageTransition]:
        return self._repository.get_transitions(journey_instance_id)

    def get_journey_timeline(self, journey_instance_id: str) -> Optional[JourneyTimeline]:
        return self._repository.get_timeline(journey_instance_id)

    def get_journeys_by_stage(self, workspace_id: str, stage: JourneyStageCode) -> List[JourneyState]:
        return self._repository.query_by_stage(workspace_id, stage)

    def get_journeys_by_status(self, workspace_id: str, status: JourneyStatus) -> List[JourneyState]:
        return self._repository.query_by_status(workspace_id, status)

    def get_journeys_by_workspace(self, workspace_id: str) -> List[JourneyState]:
        return self._repository.query_by_workspace(workspace_id)

    def get_recently_transitioned_journeys(self, workspace_id: str, since: datetime) -> List[JourneyState]:
        journeys = self._repository.query_by_workspace(workspace_id)
        recent_journeys = []
        for journey in journeys:
            if journey.last_transition_at and journey.last_transition_at >= since:
                recent_journeys.append(journey)
        return recent_journeys

default_journey_query_engine = JourneyQueryEngine(repository=default_journey_repository)
