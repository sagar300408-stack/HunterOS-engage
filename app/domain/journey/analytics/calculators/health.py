"""
Health Analytics Calculator.
Aggregates JourneyHealth across all journey maturity results.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult, JourneyHealthState
from app.domain.journey.analytics.models import JourneyHealthAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyHealthAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(self, maturity_results: List[JourneyMaturityResult]) -> JourneyHealthAnalytics:
        total = len(maturity_results)
        health_counts: Dict[str, int] = {s.value: 0 for s in JourneyHealthState}

        for mr in maturity_results:
            hv = mr.health.state.value
            health_counts[hv] = health_counts.get(hv, 0) + 1

        health_pcts = self._stats.distribution_percentages(health_counts, total)

        healthy = (
            health_counts.get("HEALTHY_PROGRESSING", 0) +
            health_counts.get("HEALTHY_STABLE", 0)
        )
        stalled = health_counts.get("STALLED", 0)
        regressing = health_counts.get("REGRESSING", 0)
        inactive = health_counts.get("INACTIVE", 0)
        insufficient = health_counts.get("INSUFFICIENT_DATA", 0)

        return JourneyHealthAnalytics(
            sample_size=total,
            health_distribution={k: v for k, v in health_counts.items() if v > 0},
            health_percentages={k: v for k, v in health_pcts.items() if health_counts.get(k, 0) > 0},
            healthy_percentage=self._stats.safe_percentage(healthy, total),
            stalled_percentage=self._stats.safe_percentage(stalled, total),
            regressing_percentage=self._stats.safe_percentage(regressing, total),
            inactive_percentage=self._stats.safe_percentage(inactive, total),
            insufficient_data_percentage=self._stats.safe_percentage(insufficient, total),
        )

default_health_analytics_calculator: JourneyHealthAnalyticsCalculator = JourneyHealthAnalyticsCalculator()
