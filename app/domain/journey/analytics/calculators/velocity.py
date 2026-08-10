"""
Velocity Analytics Calculator.
Aggregates StageVelocity across all journey maturity results.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult, StageVelocityState
from app.domain.journey.analytics.models import VelocityAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class VelocityAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(self, maturity_results: List[JourneyMaturityResult]) -> VelocityAnalytics:
        total = len(maturity_results)
        state_counts: Dict[str, int] = {s.value: 0 for s in StageVelocityState}

        tpd_vals = []
        tpw_vals = []
        avg_stage_dur_vals = []

        for mr in maturity_results:
            v = mr.velocity
            sv = v.velocity_state.value
            state_counts[sv] = state_counts.get(sv, 0) + 1
            tpd_vals.append(v.transitions_per_day)
            tpw_vals.append(v.transitions_per_week)
            avg_stage_dur_vals.append(v.average_stage_duration_days)

        state_pcts = self._stats.distribution_percentages(state_counts, total)

        return VelocityAnalytics(
            sample_size=total,
            state_counts={k: v for k, v in state_counts.items() if v > 0},
            state_percentages={k: v for k, v in state_pcts.items() if state_counts.get(k, 0) > 0},
            average_transitions_per_day=self._stats.mean(tpd_vals),
            average_transitions_per_week=self._stats.mean(tpw_vals),
            average_stage_duration_days=self._stats.mean(avg_stage_dur_vals),
        )

default_velocity_analytics_calculator: VelocityAnalyticsCalculator = VelocityAnalyticsCalculator()
