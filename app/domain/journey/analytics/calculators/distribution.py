"""
Journey Distribution Calculator
Calculates journey distribution metrics across status, type, stage, and maturity dimensions.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.models import JourneyState, JourneyStatus
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import JourneyDistributionMetrics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyDistributionCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(
        self,
        journey_states: List[JourneyState],
        maturity_results: List[JourneyMaturityResult],
    ) -> JourneyDistributionMetrics:
        """
        Calculate distribution across all journeys.
        Maturity_results is a list of latest results per journey.
        """
        total = len(journey_states)

        # Status counts
        active = sum(1 for j in journey_states if j.status == JourneyStatus.ACTIVE)
        completed = sum(1 for j in journey_states if j.status == JourneyStatus.COMPLETED)
        cancelled = sum(1 for j in journey_states if j.status == JourneyStatus.CANCELLED)
        inactive = sum(1 for j in journey_states if j.status == JourneyStatus.INACTIVE)
        lost = sum(1 for j in journey_states if j.status == JourneyStatus.LOST)

        # by_status
        status_counts = {s.value: 0 for s in JourneyStatus}
        for j in journey_states:
            status_counts[j.status.value] = status_counts.get(j.status.value, 0) + 1
        by_status = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, total)}
            for k, v in status_counts.items() if v > 0
        }

        # by_journey_type
        type_counts: Dict[str, int] = {}
        for j in journey_states:
            t = j.metadata.get("journey_type", "UNKNOWN") if j.metadata else "UNKNOWN"
            type_counts[t] = type_counts.get(t, 0) + 1
        by_journey_type = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, total)}
            for k, v in type_counts.items()
        }

        # by_current_stage
        stage_counts: Dict[str, int] = {}
        for j in journey_states:
            sc = j.current_stage.value
            stage_counts[sc] = stage_counts.get(sc, 0) + 1
        by_current_stage = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, total)}
            for k, v in stage_counts.items()
        }

        # maturity-based distributions
        mat_by_id = {str(mr.journey_id): mr for mr in maturity_results}

        maturity_level_counts: Dict[str, int] = {}
        momentum_state_counts: Dict[str, int] = {}
        stability_level_counts: Dict[str, int] = {}
        velocity_state_counts: Dict[str, int] = {}
        health_state_counts: Dict[str, int] = {}

        for j in journey_states:
            mr = mat_by_id.get(str(j.journey_instance_id))
            if mr:
                ml = mr.maturity.maturity_level.value
                maturity_level_counts[ml] = maturity_level_counts.get(ml, 0) + 1

                ms = mr.momentum.state.value
                momentum_state_counts[ms] = momentum_state_counts.get(ms, 0) + 1

                sl = mr.stability.stability_level.value
                stability_level_counts[sl] = stability_level_counts.get(sl, 0) + 1

                vs = mr.velocity.velocity_state.value
                velocity_state_counts[vs] = velocity_state_counts.get(vs, 0) + 1

                hs = mr.health.state.value
                health_state_counts[hs] = health_state_counts.get(hs, 0) + 1

        mat_total = len(mat_by_id)
        by_maturity_level = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, mat_total)}
            for k, v in maturity_level_counts.items()
        }
        by_momentum_state = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, mat_total)}
            for k, v in momentum_state_counts.items()
        }
        by_stability_level = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, mat_total)}
            for k, v in stability_level_counts.items()
        }
        by_velocity_state = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, mat_total)}
            for k, v in velocity_state_counts.items()
        }
        by_health_state = {
            k: {"count": v, "percentage": self._stats.safe_percentage(v, mat_total)}
            for k, v in health_state_counts.items()
        }

        return JourneyDistributionMetrics(
            total_journeys=total,
            active_journeys=active,
            completed_journeys=completed,
            cancelled_journeys=cancelled,
            inactive_journeys=inactive,
            archived_journeys=lost,
            by_journey_type=by_journey_type,
            by_status=by_status,
            by_current_stage=by_current_stage,
            by_maturity_level=by_maturity_level,
            by_momentum_state=by_momentum_state,
            by_stability_level=by_stability_level,
            by_velocity_state=by_velocity_state,
            by_health_state=by_health_state,
        )

default_distribution_calculator: JourneyDistributionCalculator = JourneyDistributionCalculator()
