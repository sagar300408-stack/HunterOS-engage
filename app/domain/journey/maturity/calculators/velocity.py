"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Stage Velocity Calculator

Calculates descriptive transition velocity and stage residency duration metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.domain.journey.maturity.models import (
    StageResidency,
    StageVelocity,
    StageVelocityState,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
)


class StageVelocityCalculator:
    """
    Computes deterministic velocity and progression rate indicators.
    """

    @staticmethod
    def calculate_velocity(
        journey_state: JourneyState,
        residencies: List[StageResidency],
        transitions: List[JourneyStageTransition],
        evaluated_at: Optional[datetime] = None,
    ) -> StageVelocity:
        """
        Calculate descriptive stage velocity metrics.
        """
        now = evaluated_at or datetime.now(timezone.utc)
        curr_entered_at = journey_state.stage_entered_at or journey_state.journey_started_at
        current_duration_days = max(
            0.0, (now - curr_entered_at).total_seconds() / 86400.0
        )
        total_journey_days = max(
            0.1, (now - journey_state.journey_started_at).total_seconds() / 86400.0
        )

        closed_residencies = [r for r in residencies if r.exited_at is not None]
        if closed_residencies:
            avg_duration_days = sum(r.duration_days for r in closed_residencies) / len(closed_residencies)
        else:
            avg_duration_days = current_duration_days

        trans_count = len(transitions)
        transitions_per_day = trans_count / total_journey_days
        transitions_per_week = transitions_per_day * 7.0

        # Determine velocity state
        is_terminal = journey_state.current_stage in (
            JourneyStageCode.CLOSED_WON,
            JourneyStageCode.CLOSED_LOST,
            JourneyStageCode.INACTIVE,
        ) or journey_state.status in (
            JourneyStatus.COMPLETED,
            JourneyStatus.LOST,
            JourneyStatus.INACTIVE,
            JourneyStatus.CANCELLED,
        )

        if is_terminal:
            velocity_state = StageVelocityState.NORMAL
        elif current_duration_days > 45.0:
            velocity_state = StageVelocityState.STALLED
        elif transitions_per_week >= 1.5 or (trans_count >= 2 and avg_duration_days <= 3.0):
            velocity_state = StageVelocityState.FAST
        elif transitions_per_week >= 0.35 or current_duration_days <= 14.0:
            velocity_state = StageVelocityState.NORMAL
        elif current_duration_days > 14.0:
            velocity_state = StageVelocityState.SLOW
        elif trans_count == 0 and total_journey_days < 7.0:
            velocity_state = StageVelocityState.UNKNOWN
        else:
            velocity_state = StageVelocityState.SLOW

        return StageVelocity(
            transitions_per_day=round(transitions_per_day, 4),
            transitions_per_week=round(transitions_per_week, 4),
            average_stage_duration_days=round(avg_duration_days, 2),
            current_stage_duration_days=round(current_duration_days, 2),
            historical_average_duration_days=None,
            velocity_state=velocity_state,
            calculated_at=now,
        )


default_velocity_calculator = StageVelocityCalculator()
