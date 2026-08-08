"""
HunterOS Engage V1 — Journey CQRS Repositories
Phase 2.4.1: Journey Foundation

Abstract read/write repositories and InMemory concrete implementation.
"""

from __future__ import annotations

import abc
import threading
import uuid
from typing import Dict, List, Optional, Union

from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
    JourneyTimelineEvent,
)


class JourneyReadRepository(abc.ABC):
    """Abstract read repository for Journey Intelligence (CQRS query side)."""

    @abc.abstractmethod
    def get_journey(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyState]:
        pass

    @abc.abstractmethod
    def get_current_stage(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyStageCode]:
        pass

    @abc.abstractmethod
    def get_stage_history(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageCode]:
        pass

    @abc.abstractmethod
    def get_transitions(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageTransition]:
        pass

    @abc.abstractmethod
    def get_timeline(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyTimeline]:
        pass

    @abc.abstractmethod
    def query_by_stage(self, workspace_id: Union[uuid.UUID, str], stage: JourneyStageCode) -> List[JourneyState]:
        pass

    @abc.abstractmethod
    def query_by_status(self, workspace_id: Union[uuid.UUID, str], status: JourneyStatus) -> List[JourneyState]:
        pass

    @abc.abstractmethod
    def query_by_workspace(self, workspace_id: Union[uuid.UUID, str]) -> List[JourneyState]:
        pass


class JourneyWriteRepository(abc.ABC):
    """Abstract write repository for Journey Intelligence (CQRS command side)."""

    @abc.abstractmethod
    def create_journey(self, state: JourneyState) -> None:
        pass

    @abc.abstractmethod
    def save_journey_state(self, state: JourneyState) -> None:
        pass

    @abc.abstractmethod
    def append_transition(self, journey_instance_id: Union[uuid.UUID, str], transition: JourneyStageTransition) -> None:
        pass

    @abc.abstractmethod
    def append_timeline_event(self, journey_instance_id: Union[uuid.UUID, str], event: JourneyTimelineEvent) -> None:
        pass


class InMemoryJourneyRepository(JourneyReadRepository, JourneyWriteRepository):
    """Thread-safe in-memory implementation of both read and write repositories."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._journeys: Dict[str, JourneyState] = {}

    def _key(self, journey_instance_id: Union[uuid.UUID, str]) -> str:
        return str(journey_instance_id)

    def _ws_key(self, workspace_id: Union[uuid.UUID, str]) -> str:
        return str(workspace_id)

    # ── Read Operations ──────────────────────────────────────────────────

    def get_journey(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyState]:
        with self._lock:
            return self._journeys.get(self._key(journey_instance_id))

    def get_current_stage(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyStageCode]:
        with self._lock:
            journey = self._journeys.get(self._key(journey_instance_id))
            return journey.current_stage if journey else None

    def get_stage_history(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageCode]:
        with self._lock:
            journey = self._journeys.get(self._key(journey_instance_id))
            if journey is None:
                return []
            return list(journey.stage_history)

    def get_transitions(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageTransition]:
        with self._lock:
            journey = self._journeys.get(self._key(journey_instance_id))
            if journey is None:
                return []
            return list(journey.transitions)

    def get_timeline(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyTimeline]:
        with self._lock:
            journey = self._journeys.get(self._key(journey_instance_id))
            if journey is None:
                return None
            return journey.timeline

    def query_by_stage(self, workspace_id: Union[uuid.UUID, str], stage: JourneyStageCode) -> List[JourneyState]:
        with self._lock:
            ws = self._ws_key(workspace_id)
            return [
                j for j in self._journeys.values()
                if str(j.workspace_id) == ws and j.current_stage == stage
            ]

    def query_by_status(self, workspace_id: Union[uuid.UUID, str], status: JourneyStatus) -> List[JourneyState]:
        with self._lock:
            ws = self._ws_key(workspace_id)
            return [
                j for j in self._journeys.values()
                if str(j.workspace_id) == ws and j.status == status
            ]

    def query_by_workspace(self, workspace_id: Union[uuid.UUID, str]) -> List[JourneyState]:
        with self._lock:
            ws = self._ws_key(workspace_id)
            return [
                j for j in self._journeys.values()
                if str(j.workspace_id) == ws
            ]

    # ── Write Operations ─────────────────────────────────────────────────

    def create_journey(self, state: JourneyState) -> None:
        with self._lock:
            self._journeys[self._key(state.journey_instance_id)] = state

    def save_journey_state(self, state: JourneyState) -> None:
        with self._lock:
            self._journeys[self._key(state.journey_instance_id)] = state

    def append_transition(
        self, journey_instance_id: Union[uuid.UUID, str], transition: JourneyStageTransition,
    ) -> None:
        with self._lock:
            key = self._key(journey_instance_id)
            journey = self._journeys.get(key)
            if journey is not None:
                if transition not in journey.transitions:
                    journey.transitions.append(transition)

    def append_timeline_event(
        self, journey_instance_id: Union[uuid.UUID, str], event: JourneyTimelineEvent,
    ) -> None:
        with self._lock:
            key = self._key(journey_instance_id)
            journey = self._journeys.get(key)
            if journey is not None and journey.timeline is not None:
                current_events = list(journey.timeline.events)
                current_events.append(event)
                journey.timeline = JourneyTimeline(
                    timeline_id=journey.timeline.timeline_id,
                    journey_instance_id=journey.journey_instance_id,
                    workspace_id=journey.workspace_id,
                    events=current_events,
                )


default_journey_repository: InMemoryJourneyRepository = InMemoryJourneyRepository()
