"""
Observed Outcome Analytics Calculator.
Calculates historical observed stage-to-outcome rates.
Strictly historical. No prediction. No small-sample fabrication.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Union, Any

from app.domain.journey.models import JourneyState, JourneyStatus
from app.domain.journey.analytics.models import ObservedStageOutcomeAnalytics, OutcomeDataStatus
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine
from app.domain.journey.analytics.statistics.confidence import calculate_proportion_ci

class ObservedOutcomeCalculator:
    def __init__(
        self,
        stats: DescriptiveStatisticsEngine = default_stats_engine,
        minimum_sample: int = 30,
    ) -> None:
        self._stats = stats
        self._minimum_sample = minimum_sample

    def calculate(
        self,
        journey_states: List[JourneyState],
        workspace_id: Union[str, Any],
        stages_to_analyze: Optional[List[str]] = None,
        target_outcome: str = "CLOSED_WON",
        observation_window_days: int = 365,
        confidence_level: float = 0.95,
    ) -> Dict[str, ObservedStageOutcomeAnalytics]:
        """
        For each stage, calculate the historical observed rate of reaching target_outcome
        among journeys that reached that stage AND have reached a terminal state.
        """
        ws_str = str(workspace_id)
        terminal_statuses = {JourneyStatus.COMPLETED, JourneyStatus.LOST, JourneyStatus.CANCELLED, JourneyStatus.INACTIVE}
        terminal_stages_set = {"CLOSED_WON", "CLOSED_LOST", "INACTIVE"}

        # Only workspace-isolated, terminal journeys count
        historical = [
            j for j in journey_states
            if str(j.workspace_id) == ws_str
            and (j.status in terminal_statuses or j.current_stage.value in terminal_stages_set)
        ]

        # Collect all unique stages
        if stages_to_analyze:
            all_stages = stages_to_analyze
        else:
            all_stages_set: set = set()
            for j in historical:
                all_stages_set.update(s.value for s in j.stage_history)
                all_stages_set.add(j.current_stage.value)
            all_stages = list(all_stages_set)

        result: Dict[str, ObservedStageOutcomeAnalytics] = {}
        for stage in all_stages:
            # Journeys that reached this stage
            reached = [
                j for j in historical
                if stage in [s.value for s in j.stage_history] or j.current_stage.value == stage
            ]
            sample_size = len(reached)
            success_count = sum(
                1 for j in reached
                if j.current_stage.value == "CLOSED_WON" or j.status == JourneyStatus.COMPLETED
            ) if target_outcome == "CLOSED_WON" else 0
            failure_count = sample_size - success_count

            limitations = []
            if sample_size < self._minimum_sample:
                limitations.append(
                    f"Insufficient sample: {sample_size} historical journeys, minimum {self._minimum_sample} required."
                )
                result[stage] = ObservedStageOutcomeAnalytics(
                    stage=stage,
                    outcome=target_outcome,
                    success_count=success_count,
                    failure_count=failure_count,
                    sample_size=sample_size,
                    observed_rate=None,
                    observation_window_days=observation_window_days,
                    minimum_sample_met=False,
                    confidence_interval_lower=None,
                    confidence_interval_upper=None,
                    confidence_level=confidence_level,
                    calculation_method="WILSON_SCORE_INTERVAL",
                    limitations=limitations,
                    data_status=OutcomeDataStatus.INSUFFICIENT_DATA,
                )
            else:
                ci = calculate_proportion_ci(success_count, sample_size, confidence_level, self._minimum_sample)
                limitations.append(
                    f"Descriptive historical rate based on {sample_size} completed journeys "
                    f"that reached stage '{stage}' in workspace {ws_str}."
                )
                result[stage] = ObservedStageOutcomeAnalytics(
                    stage=stage,
                    outcome=target_outcome,
                    success_count=success_count,
                    failure_count=failure_count,
                    sample_size=sample_size,
                    observed_rate=ci.point_estimate,
                    observation_window_days=observation_window_days,
                    minimum_sample_met=True,
                    confidence_interval_lower=ci.lower_bound,
                    confidence_interval_upper=ci.upper_bound,
                    confidence_level=confidence_level,
                    calculation_method="WILSON_SCORE_INTERVAL",
                    limitations=limitations,
                    data_status=OutcomeDataStatus.CALCULATED,
                )
        return result

default_outcome_calculator: ObservedOutcomeCalculator = ObservedOutcomeCalculator()
