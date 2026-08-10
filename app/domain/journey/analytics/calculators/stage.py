"""
Stage Analytics Calculator
Per-stage journey count, residency statistics.
"""
from __future__ import annotations
from typing import List, Dict

from app.domain.journey.models import JourneyState
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import StageAnalytics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class StageAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(
        self,
        journey_states: List[JourneyState],
        maturity_results: List[JourneyMaturityResult],
    ) -> Dict[str, StageAnalytics]:
        """
        For each stage observed, calculate journey count, residency stats.
        Returns dict keyed by stage code value.
        """
        total = len(journey_states)
        mat_by_id = {str(mr.journey_id): mr for mr in maturity_results}

        # Collect all residency records across all journeys per stage
        residencies_by_stage: Dict[str, List[float]] = {}  # stage -> list of duration_days
        entries_by_stage: Dict[str, set] = {}  # stage -> set of journey_ids that entered
        exits_by_stage: Dict[str, set] = {}  # stage -> set of journey_ids that exited
        current_by_stage: Dict[str, int] = {}  # stage -> count currently in this stage
        completed_by_stage: Dict[str, int] = {}  # stage -> count of completed residencies

        for j in journey_states:
            mr = mat_by_id.get(str(j.journey_instance_id))
            if mr:
                for res in mr.stage_residency:
                    stage_val = res.stage.value
                    if stage_val not in residencies_by_stage:
                        residencies_by_stage[stage_val] = []
                        entries_by_stage[stage_val] = set()
                        exits_by_stage[stage_val] = set()
                    residencies_by_stage[stage_val].append(res.duration_days)
                    entries_by_stage[stage_val].add(str(j.journey_instance_id))
                    if res.exited_at is not None:
                        exits_by_stage[stage_val].add(str(j.journey_instance_id))
                        completed_by_stage[stage_val] = completed_by_stage.get(stage_val, 0) + 1
                    else:
                        current_by_stage[stage_val] = current_by_stage.get(stage_val, 0) + 1

        # Also add journeys not in maturity results (just by current stage)
        stage_journey_counts: Dict[str, int] = {}
        for j in journey_states:
            sv = j.current_stage.value
            stage_journey_counts[sv] = stage_journey_counts.get(sv, 0) + 1

        all_stages = set(stage_journey_counts.keys()) | set(residencies_by_stage.keys())

        result: Dict[str, StageAnalytics] = {}
        for stage_val in all_stages:
            durations = residencies_by_stage.get(stage_val, [])
            journey_count = stage_journey_counts.get(stage_val, 0)
            result[stage_val] = StageAnalytics(
                stage=stage_val,
                journey_count=journey_count,
                percentage_of_journeys=self._stats.safe_percentage(journey_count, total),
                unique_entries=len(entries_by_stage.get(stage_val, set())),
                unique_exits=len(exits_by_stage.get(stage_val, set())),
                current_residency_count=current_by_stage.get(stage_val, 0),
                completed_residency_count=completed_by_stage.get(stage_val, 0),
                average_residency_days=self._stats.mean(durations),
                median_residency_days=self._stats.median(durations),
                minimum_residency_days=self._stats.minimum(durations),
                maximum_residency_days=self._stats.maximum(durations),
                p25_residency_days=self._stats.percentile(durations, 25) if len(durations) >= 4 else None,
                p75_residency_days=self._stats.percentile(durations, 75) if len(durations) >= 4 else None,
            )
        return result

default_stage_analytics_calculator: StageAnalyticsCalculator = StageAnalyticsCalculator()
