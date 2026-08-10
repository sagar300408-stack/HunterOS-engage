"""
Maturity Analytics Calculator.
Aggregates JourneyMaturity results across all journeys.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import MaturityAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class MaturityAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(self, maturity_results: List[JourneyMaturityResult]) -> MaturityAnalytics:
        scores = [mr.maturity.maturity_score for mr in maturity_results]
        level_counts: Dict[str, int] = {}
        for mr in maturity_results:
            lv = mr.maturity.maturity_level.value
            level_counts[lv] = level_counts.get(lv, 0) + 1

        total = len(maturity_results)
        level_pcts = self._stats.distribution_percentages(level_counts, total)

        # lowest_bucket = level with highest count at bottom quartile
        lowest_bucket = None
        highest_bucket = None
        if level_counts:
            sorted_levels = sorted(level_counts.items(), key=lambda x: x[1], reverse=True)
            all_level_order = ["INITIAL", "EARLY", "DEVELOPING", "QUALIFIED", "ADVANCED", "LATE_STAGE", "COMPLETED"]
            # lowest: highest count among bottom 3 levels
            bottom_levels = [l for l in all_level_order[:3] if l in level_counts]
            if bottom_levels:
                lowest_bucket = max(bottom_levels, key=lambda l: level_counts.get(l, 0))
            top_levels = [l for l in all_level_order[-3:] if l in level_counts]
            if top_levels:
                highest_bucket = max(top_levels, key=lambda l: level_counts.get(l, 0))

        return MaturityAnalytics(
            sample_size=total,
            average_maturity_score=self._stats.mean(scores),
            median_maturity_score=self._stats.median(scores),
            lowest_maturity_score=self._stats.minimum(scores),
            highest_maturity_score=self._stats.maximum(scores),
            maturity_level_counts=level_counts,
            maturity_level_percentages=level_pcts,
            lowest_maturity_bucket=lowest_bucket,
            highest_maturity_bucket=highest_bucket,
        )

default_maturity_analytics_calculator: MaturityAnalyticsCalculator = MaturityAnalyticsCalculator()
