"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Momentum Calculator

Descriptive evaluation of recent observed stage movement direction and velocity.
Derived purely from historical transitions. Never predicts future movement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.domain.journey.maturity.models import (
    JourneyMomentum,
    JourneyMomentumState,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    TransitionType,
)


class JourneyMomentumCalculator:
    """
    Evaluates observed recent momentum without predictive assertions.
    """

    @staticmethod
    def calculate_momentum(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        evaluated_at: Optional[datetime] = None,
    ) -> JourneyMomentum:
        """
        Calculate descriptive momentum metrics from observed transitions.
        """
        now = evaluated_at or datetime.now(timezone.utc)
        sorted_transitions = sorted(transitions, key=lambda t: t.occurred_at)

        # Inactive / Terminal checks
        if journey_state.current_stage in (JourneyStageCode.CLOSED_WON, JourneyStageCode.CLOSED_LOST) or journey_state.status in (
            JourneyStatus.COMPLETED,
            JourneyStatus.LOST,
            JourneyStatus.INACTIVE,
            JourneyStatus.CANCELLED,
        ):
            return JourneyMomentum(
                state=JourneyMomentumState.STABLE,
                momentum_score=0.0,
                recent_advancements_count=0,
                recent_regressions_count=0,
                days_since_last_transition=0.0,
                transition_frequency_per_week=0.0,
                description="Journey has reached a terminal stage and is permanently stable.",
                calculated_at=now,
            )

        if not sorted_transitions:
            journey_age_days = (now - journey_state.journey_started_at).total_seconds() / 86400.0
            if journey_age_days > 45:
                state = JourneyMomentumState.INACTIVE
                score = -0.5
                desc = f"Journey has remained at entry stage without transition for {journey_age_days:.1f} days."
            else:
                state = JourneyMomentumState.UNKNOWN
                score = 0.0
                desc = "New journey with no observed stage transitions recorded yet."

            return JourneyMomentum(
                state=state,
                momentum_score=score,
                recent_advancements_count=0,
                recent_regressions_count=0,
                days_since_last_transition=round(journey_age_days, 2),
                transition_frequency_per_week=0.0,
                description=desc,
                calculated_at=now,
            )

        # Analyze recent transitions
        last_transition = sorted_transitions[-1]
        days_since_last = max(
            0.0, (now - last_transition.occurred_at).total_seconds() / 86400.0
        )

        total_journey_days = max(
            1.0, (now - journey_state.journey_started_at).total_seconds() / 86400.0
        )
        transitions_per_week = (len(sorted_transitions) / total_journey_days) * 7.0

        # Look at last 3 transitions or transitions in last 30 days
        recent_window_transitions = [
            t for t in sorted_transitions if (now - t.occurred_at).total_seconds() <= 30 * 86400
        ]
        if not recent_window_transitions:
            recent_window_transitions = sorted_transitions[-3:]

        advancements = sum(
            1
            for t in recent_window_transitions
            if t.transition_type in (TransitionType.ADVANCE, TransitionType.COMPLETION)
        )
        regressions = sum(
            1 for t in recent_window_transitions if t.transition_type == TransitionType.REGRESSION
        )

        # Determine state and score
        if days_since_last > 60:
            state = JourneyMomentumState.INACTIVE
            score = -0.7
            desc = f"Observed journey inactivity: no stage transitions for {days_since_last:.1f} days."
        elif days_since_last > 30 and regressions == 0 and advancements == 0:
            state = JourneyMomentumState.WEAKENING
            score = -0.3
            desc = f"Journey momentum has weakened with {days_since_last:.1f} days in current stage."
        elif regressions > advancements:
            state = JourneyMomentumState.REGRESSING
            score = -0.6
            desc = f"Journey exhibits recent regression ({regressions} observed stage regressions)."
        elif advancements >= 2:
            state = JourneyMomentumState.STRONGLY_ADVANCING
            score = 0.85
            desc = f"Journey demonstrates strong recent progression ({advancements} stage advancements)."
        elif advancements == 1 and days_since_last <= 14:
            state = JourneyMomentumState.ADVANCING
            score = 0.60
            desc = "Journey demonstrates recent evidence-backed stage advancement."
        else:
            state = JourneyMomentumState.STABLE
            score = 0.20
            desc = "Journey is progressing steadily with stable observed stage residency."

        return JourneyMomentum(
            state=state,
            momentum_score=round(score, 4),
            recent_advancements_count=advancements,
            recent_regressions_count=regressions,
            days_since_last_transition=round(days_since_last, 2),
            transition_frequency_per_week=round(transitions_per_week, 2),
            description=desc,
            calculated_at=now,
        )


default_momentum_calculator = JourneyMomentumCalculator()
