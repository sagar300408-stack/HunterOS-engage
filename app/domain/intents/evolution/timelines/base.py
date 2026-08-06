"""
HunterOS Engage V1 - Timeline Builder Base & Velocity Calculator
Abstract base for projecting timelines from the immutable evolution event stream and snapshots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
    IntentTimeline,
    IntentVelocity,
)


class AbstractTimelineBuilder(ABC):
    """
    Abstract builder projecting historical snapshots and event streams into a unified IntentTimeline.
    """

    def __init__(self, entity_type: EntityType):
        self.entity_type: EntityType = entity_type

    @abstractmethod
    def build_timeline(
        self,
        intent_id: uuid.UUID,
        entity_id: str,
        snapshots: List[IntentStateSnapshot],
        events: List[IntentEvolutionEvent],
        transitions: List[IntentStateTransition],
    ) -> IntentTimeline:
        """Project the timeline from available historical snapshots and events."""
        pass

    def calculate_velocity(self, snapshots: List[IntentStateSnapshot]) -> IntentVelocity:
        """
        Deterministically calculate historical observation velocity based on timestamps.
        Zero forecasting or prediction.
        """
        if len(snapshots) < 2:
            return IntentVelocity.UNKNOWN

        sorted_snaps = sorted(snapshots, key=lambda s: s.observed_at)
        intervals: List[float] = []

        for i in range(1, len(sorted_snaps)):
            diff_seconds = (
                sorted_snaps[i].observed_at - sorted_snaps[i - 1].observed_at
            ).total_seconds()
            intervals.append(max(diff_seconds, 1.0))

        if len(intervals) >= 2:
            # If recent interval is notably shorter than previous interval -> INCREASING
            if intervals[-1] < intervals[-2] * 0.75:
                return IntentVelocity.INCREASING
            elif intervals[-1] > intervals[-2] * 1.5:
                return IntentVelocity.DECREASING
            else:
                return IntentVelocity.STABLE
        elif len(intervals) == 1:
            return IntentVelocity.STABLE

        return IntentVelocity.SPORADIC
