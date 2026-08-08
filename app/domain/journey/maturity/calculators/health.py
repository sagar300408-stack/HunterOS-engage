"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Health Evaluator

Rule-based deterministic structural health classification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.domain.journey.maturity.models import (
    JourneyHealth,
    JourneyHealthState,
    JourneyMaturity,
    JourneyMomentum,
    JourneyMomentumState,
    JourneyStability,
    JourneyStabilityLevel,
    StageVelocity,
    StageVelocityState,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
)


class JourneyHealthCalculator:
    """
    Evaluates descriptive structural journey health.
    """

    @staticmethod
    def calculate_health(
        journey_state: JourneyState,
        maturity: JourneyMaturity,
        momentum: JourneyMomentum,
        stability: JourneyStability,
        velocity: StageVelocity,
        evaluated_at: Optional[datetime] = None,
    ) -> JourneyHealth:
        """
        Evaluate structural journey health from combined metrics.
        """
        now = evaluated_at or datetime.now(timezone.utc)

        # Terminal completed state
        if journey_state.current_stage == JourneyStageCode.CLOSED_WON or journey_state.status == JourneyStatus.COMPLETED:
            return JourneyHealth(
                state=JourneyHealthState.HEALTHY_STABLE,
                summary="Journey successfully completed with closed-won outcome.",
                factors={"status": "COMPLETED", "maturity_score": maturity.maturity_score},
                calculated_at=now,
            )

        # Terminal lost / inactive state
        if journey_state.current_stage in (JourneyStageCode.CLOSED_LOST, JourneyStageCode.INACTIVE) or journey_state.status in (
            JourneyStatus.LOST,
            JourneyStatus.INACTIVE,
            JourneyStatus.CANCELLED,
        ):
            return JourneyHealth(
                state=JourneyHealthState.INACTIVE,
                summary="Journey has reached a terminal non-converting or inactive state.",
                factors={"status": journey_state.status.value, "stage": journey_state.current_stage.value},
                calculated_at=now,
            )

        # Check for inactive / stalled
        if momentum.state == JourneyMomentumState.INACTIVE:
            state = JourneyHealthState.INACTIVE
            summary = "Journey is inactive with prolonged absence of observed activity."
        elif velocity.velocity_state == StageVelocityState.STALLED:
            state = JourneyHealthState.STALLED
            summary = f"Journey is stalled in stage '{journey_state.current_stage.value}' exceeding duration threshold."
        elif momentum.state == JourneyMomentumState.REGRESSING or stability.stability_level in (
            JourneyStabilityLevel.UNSTABLE,
            JourneyStabilityLevel.HIGHLY_UNSTABLE,
        ):
            state = JourneyHealthState.REGRESSING
            summary = "Journey exhibits stage regressions or high state instability."
        elif momentum.state in (JourneyMomentumState.STRONGLY_ADVANCING, JourneyMomentumState.ADVANCING) and stability.stability_level in (
            JourneyStabilityLevel.VERY_STABLE,
            JourneyStabilityLevel.STABLE,
            JourneyStabilityLevel.MODERATE,
        ):
            state = JourneyHealthState.HEALTHY_PROGRESSING
            summary = "Journey is progressing healthily with recent evidence-backed stage advancements."
        elif velocity.velocity_state == StageVelocityState.SLOW or maturity.stage_duration_days > 21.0:
            state = JourneyHealthState.SLOW_PROGRESSING
            summary = "Journey is progressing at a slower rate than typical stage residency."
        elif stability.stability_level in (JourneyStabilityLevel.VERY_STABLE, JourneyStabilityLevel.STABLE):
            state = JourneyHealthState.HEALTHY_STABLE
            summary = "Journey is stable with consistent stage residency."
        elif maturity.completed_stage_count == 0 and maturity.stage_position <= 1:
            state = JourneyHealthState.INSUFFICIENT_DATA
            summary = "Early journey with limited observed progression history."
        else:
            state = JourneyHealthState.HEALTHY_STABLE
            summary = "Journey exhibits steady baseline state."

        factors: Dict[str, Any] = {
            "momentum_state": momentum.state.value,
            "stability_level": stability.stability_level.value,
            "velocity_state": velocity.velocity_state.value,
            "maturity_level": maturity.maturity_level.value,
            "stage_duration_days": maturity.stage_duration_days,
            "stability_score": stability.stability_score,
            "momentum_score": momentum.momentum_score,
        }

        return JourneyHealth(
            state=state,
            summary=summary,
            factors=factors,
            calculated_at=now,
        )


default_health_calculator = JourneyHealthCalculator()
