"""
Stage Residency Analytics Calculator.
Aggregates Phase 2.4.3 StageResidency records for workspace-level analytics.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.maturity.models import JourneyMaturityResult, StageResidency
from app.domain.journey.analytics.models import StageResidencyAnalytics
from app.domain.journey.analytics.configuration import JourneyAnalyticsConfiguration
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class StageResidencyAnalyticsCalculator:
    def __init__(
        self,
        stats: DescriptiveStatisticsEngine = default_stats_engine,
    ) -> None:
        self._stats = stats

    def calculate(
        self,
        maturity_results: List[JourneyMaturityResult],
        configuration: JourneyAnalyticsConfiguration,
    ) -> Dict[str, StageResidencyAnalytics]:
        """
        Aggregate StageResidency from all maturity results per stage.
        """
        # Collect all residencies by stage
        by_stage: Dict[str, List[StageResidency]] = {}
        for mr in maturity_results:
            for res in mr.stage_residency:
                sv = res.stage.value
                if sv not in by_stage:
                    by_stage[sv] = []
                by_stage[sv].append(res)

        result: Dict[str, StageResidencyAnalytics] = {}
        for stage_val, residencies in by_stage.items():
            durations = [r.duration_days for r in residencies]
            current_count = sum(1 for r in residencies if r.status.value == "ACTIVE")

            total = len(residencies)
            reentries = sum(r.reentry_count for r in residencies)
            reentry_rate = self._stats.safe_ratio(reentries, total)

            # Oscillation: journeys with > 1 reentry in any stage
            oscillating = sum(1 for r in residencies if r.reentry_count > 1)
            oscillation_rate = self._stats.safe_ratio(oscillating, total)

            avg_dur = self._stats.mean(durations)
            cat = configuration.get_residency_category(avg_dur or 0.0)

            result[stage_val] = StageResidencyAnalytics(
                stage=stage_val,
                sample_size=total,
                average_duration_days=avg_dur,
                median_duration_days=self._stats.median(durations),
                p25_days=self._stats.percentile(durations, 25) if len(durations) >= 4 else None,
                p75_days=self._stats.percentile(durations, 75) if len(durations) >= 4 else None,
                minimum_days=self._stats.minimum(durations),
                maximum_days=self._stats.maximum(durations),
                reentry_rate=reentry_rate,
                oscillation_rate=oscillation_rate,
                current_residency_count=current_count,
                residency_category=cat,
            )
        return result

default_residency_analytics_calculator: StageResidencyAnalyticsCalculator = StageResidencyAnalyticsCalculator()
