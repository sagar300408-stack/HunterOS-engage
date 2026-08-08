"""
HunterOS Engage V1 — Journey Definition Registries
Phase 2.4.1: Journey Foundation

Thread-safe registries for journey and stage definitions.
"""

from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional, Tuple, Union

from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageCode,
    JourneyType,
    StageDefinition,
)
from app.domain.journey.exceptions import JourneyDefinitionError


class StageDefinitionRegistry:
    """Thread-safe registry for stage definitions indexed by (journey_type, stage_code)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stages: Dict[Tuple[str, str], StageDefinition] = {}

    def register(self, stage_def: StageDefinition) -> None:
        """Register a stage definition."""
        with self._lock:
            key = (stage_def.journey_type.value, stage_def.stage_code.value)
            self._stages[key] = stage_def

    def get(self, stage_code: JourneyStageCode, journey_type: JourneyType) -> Optional[StageDefinition]:
        """Get a stage definition by code and journey type."""
        with self._lock:
            return self._stages.get((journey_type.value, stage_code.value))

    def list(self, journey_type: Optional[JourneyType] = None) -> List[StageDefinition]:
        """List stage definitions, optionally filtered by journey type."""
        with self._lock:
            if journey_type is None:
                return list(self._stages.values())
            return [s for s in self._stages.values() if s.journey_type == journey_type]

    def exists(self, stage_code: JourneyStageCode, journey_type: JourneyType) -> bool:
        """Check if a stage definition exists."""
        with self._lock:
            return (journey_type.value, stage_code.value) in self._stages

    def resolve(self, stage_code: JourneyStageCode, journey_type: JourneyType) -> StageDefinition:
        """Resolve a stage definition or raise."""
        with self._lock:
            stage = self.get(stage_code, journey_type)
            if stage is None:
                raise JourneyDefinitionError(
                    f"Stage definition not found: {journey_type.value}/{stage_code.value}"
                )
            return stage

    def remove(self, stage_code: JourneyStageCode, journey_type: JourneyType) -> None:
        """Remove a stage definition."""
        with self._lock:
            key = (journey_type.value, stage_code.value)
            self._stages.pop(key, None)


class JourneyDefinitionRegistry:
    """Thread-safe registry for journey definitions."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: Dict[str, JourneyDefinition] = {}
        self._by_type: Dict[str, JourneyDefinition] = {}

    def register(self, journey_def: JourneyDefinition) -> None:
        """Register a journey definition."""
        with self._lock:
            self._by_id[str(journey_def.journey_id)] = journey_def
            self._by_type[journey_def.journey_type.value] = journey_def

    def get(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyDefinition]:
        """Get a journey definition by ID."""
        with self._lock:
            return self._by_id.get(str(journey_id))

    def get_by_type(self, journey_type: JourneyType) -> Optional[JourneyDefinition]:
        """Get a journey definition by type."""
        with self._lock:
            return self._by_type.get(journey_type.value)

    def list(self) -> List[JourneyDefinition]:
        """List all registered journey definitions."""
        with self._lock:
            return list(self._by_id.values())

    def exists(self, journey_id: Union[uuid.UUID, str]) -> bool:
        """Check if a journey definition exists."""
        with self._lock:
            return str(journey_id) in self._by_id

    def resolve(self, journey_type: JourneyType) -> JourneyDefinition:
        """Resolve a journey definition by type or raise."""
        with self._lock:
            definition = self.get_by_type(journey_type)
            if definition is None:
                raise JourneyDefinitionError(
                    f"Journey definition not found for type: {journey_type.value}"
                )
            return definition

    def remove(self, journey_id: Union[uuid.UUID, str]) -> None:
        """Remove a journey definition."""
        with self._lock:
            key = str(journey_id)
            if key in self._by_id:
                definition = self._by_id.pop(key)
                type_key = definition.journey_type.value
                if type_key in self._by_type:
                    if str(self._by_type[type_key].journey_id) == key:
                        del self._by_type[type_key]


default_stage_registry: StageDefinitionRegistry = StageDefinitionRegistry()
default_journey_registry: JourneyDefinitionRegistry = JourneyDefinitionRegistry()
