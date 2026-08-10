"""
Momentum Analytics Calculator.
Aggregates JourneyMomentum across all journey maturity results.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult, JourneyMomentumState
from app.domain.journey.analytics.models import MomentumAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class MomentumAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(self, maturity_results: List[JourneyMaturityResult]) -> MomentumAnalytics:
        total = len(maturity_results)
        state_counts: Dict[str, int] = {s.value: 0 for s in JourneyMomentumState}

        for mr in maturity_results:
            sv = mr.momentum.state.value
            state_counts[sv] = state_counts.get(sv, 0) + 1

        state_pcts = self._stats.distribution_percentages(state_counts, total)

        advancing = state_counts.get("STRONGLY_ADVANCING", 0) + state_counts.get("ADVANCING", 0)
        stable = state_counts.get("STABLE", 0)
        weakening = state_counts.get("WEAKENING", 0)
        regressing = state_counts.get("REGRESSING", 0)
        inactive = state_counts.get("INACTIVE", 0)
        unknown = state_counts.get("UNKNOWN", 0)

        return MomentumAnalytics(
            sample_size=total,
            state_counts={k: v for k, v in state_counts.items() if v > 0},
            state_percentages={k: v for k, v in state_pcts.items() if state_counts.get(k, 0) > 0},
            advancing_percentage=self._stats.safe_percentage(advancing, total),
            stable_percentage=self._stats.safe_percentage(stable, total),
            weakening_percentage=self._stats.safe_percentage(weakening, total),
            regressing_percentage=self._stats.safe_percentage(regressing, total),
            inactive_percentage=self._stats.safe_percentage(inactive, total),
            unknown_percentage=self._stats.safe_percentage(unknown, total),
        )

default_momentum_analytics_calculator: MomentumAnalyticsCalculator = MomentumAnalyticsCalculator()
