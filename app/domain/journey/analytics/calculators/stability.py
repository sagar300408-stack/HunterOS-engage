"""
Stability Analytics Calculator.
Aggregates JourneyStability across all journey maturity results.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult, JourneyStabilityLevel
from app.domain.journey.analytics.models import StabilityAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class StabilityAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(self, maturity_results: List[JourneyMaturityResult]) -> StabilityAnalytics:
        total = len(maturity_results)
        level_counts: Dict[str, int] = {s.value: 0 for s in JourneyStabilityLevel}

        scores = []
        reentries = []
        oscillations = []
        conflicting = []

        for mr in maturity_results:
            s = mr.stability
            sv = s.stability_level.value
            level_counts[sv] = level_counts.get(sv, 0) + 1
            scores.append(s.stability_score)
            reentries.append(float(s.stage_reentry_count))
            conflicting.append(float(s.conflicting_evidence_count))
            # Use reentry count as proxy for oscillation too
            oscillations.append(float(max(0, s.stage_reentry_count - 1)))

        level_pcts = self._stats.distribution_percentages(level_counts, total)

        return StabilityAnalytics(
            sample_size=total,
            level_counts={k: v for k, v in level_counts.items() if v > 0},
            level_percentages={k: v for k, v in level_pcts.items() if level_counts.get(k, 0) > 0},
            average_stability_score=self._stats.mean(scores),
            reentry_frequency=self._stats.mean(reentries) or 0.0,
            oscillation_frequency=self._stats.mean(oscillations) or 0.0,
            conflicting_evidence_frequency=self._stats.mean(conflicting) or 0.0,
        )

default_stability_analytics_calculator: StabilityAnalyticsCalculator = StabilityAnalyticsCalculator()
