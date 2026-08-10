"""
Funnel Analytics Calculator.
Builds sequential stage funnel from actual observed journey history.
Handles forward progression, regression, re-entry, and skipped stages.
"""
from __future__ import annotations
from typing import List

from app.domain.journey.models import JourneyState
from app.domain.journey.analytics.models import JourneyFunnelMetrics, JourneyFunnelStageMetrics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyFunnelCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(
        self,
        journey_states: List[JourneyState],
        funnel_stages: List[str],  # ordered sequence of stage codes
        minimum_sample: int = 30,
    ) -> JourneyFunnelMetrics:
        """
        Build funnel analytics from observed stage histories.
        funnel_stages is the configured ordered sequence.
        """
        total = len(journey_states)
        if not funnel_stages:
            return self._empty_funnel(funnel_stages, total)

        stage_metrics: List[JourneyFunnelStageMetrics] = []
        has_regressions = False
        has_skip_patterns = False

        terminal_outcomes = {"CLOSED_WON", "CLOSED_LOST"}

        for idx, stage in enumerate(funnel_stages):
            entered = 0
            advanced = 0
            regressed = 0
            exited_count = 0
            remaining = 0

            for j in journey_states:
                history = [s.value for s in j.stage_history]
                current = j.current_stage.value
                all_stages = history + ([current] if current not in history else [])

                if stage not in all_stages:
                    continue
                entered += 1

                # Did they advance to next stage?
                if idx < len(funnel_stages) - 1:
                    next_stage = funnel_stages[idx + 1]
                    if next_stage in all_stages:
                        advanced += 1
                    elif current == stage:
                        remaining += 1
                    elif current in terminal_outcomes:
                        exited_count += 1
                    # Check regression (went backward)
                    stage_idx_in_history = None
                    for hi, hs in enumerate(history):
                        if hs == stage:
                            stage_idx_in_history = hi
                    if stage_idx_in_history is not None and stage_idx_in_history > 0:
                        prev = history[stage_idx_in_history - 1]
                        if prev in funnel_stages and funnel_stages.index(prev) > idx:
                            regressed += 1
                            has_regressions = True

                # Detect skip patterns (reached this stage but skipped prior ones)
                if idx > 0:
                    prev_stage = funnel_stages[idx - 1]
                    if prev_stage not in all_stages:
                        has_skip_patterns = True

                # Terminal exit without advancing
                if current in terminal_outcomes and stage in all_stages:
                    if idx < len(funnel_stages) - 1 and funnel_stages[idx + 1] not in all_stages:
                        exited_count += 1

            # Historical completion rate for this stage (only if sufficient sample)
            hist_rate = None
            if entered >= minimum_sample and entered > 0:
                hist_rate = round(advanced / entered, 4) if idx < len(funnel_stages) - 1 else None

            # For last stage, completion = reaching terminal CLOSED_WON
            if idx == len(funnel_stages) - 1 and entered >= minimum_sample:
                won = sum(
                    1 for j in journey_states
                    if stage in [s.value for s in j.stage_history] + [j.current_stage.value]
                    and j.current_stage.value == "CLOSED_WON"
                )
                hist_rate = round(won / entered, 4) if entered > 0 else None

            stage_metrics.append(JourneyFunnelStageMetrics(
                stage=stage,
                sequence=idx,
                entered_count=entered,
                advanced_count=advanced,
                regressed_count=regressed,
                exited_count=exited_count,
                remaining_count=remaining,
                historical_completion_rate=hist_rate,
            ))

        # Overall metrics
        total_entered = stage_metrics[0].entered_count if stage_metrics else 0
        total_completed = stage_metrics[-1].entered_count if stage_metrics else 0
        overall_rate = None
        if total_entered >= minimum_sample and total_entered > 0:
            overall_rate = round(total_completed / total_entered, 4)

        return JourneyFunnelMetrics(
            funnel_stages=funnel_stages,
            stage_metrics=stage_metrics,
            total_entered=total_entered,
            total_completed=total_completed,
            overall_completion_rate=overall_rate,
            has_regressions=has_regressions,
            has_skip_patterns=has_skip_patterns,
        )

    def _empty_funnel(self, funnel_stages: List[str], total: int) -> JourneyFunnelMetrics:
        return JourneyFunnelMetrics(
            funnel_stages=funnel_stages,
            stage_metrics=[],
            total_entered=0,
            total_completed=0,
            overall_completion_rate=None,
            has_regressions=False,
            has_skip_patterns=False,
        )

default_funnel_calculator: JourneyFunnelCalculator = JourneyFunnelCalculator()
