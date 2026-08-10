"""
Transition Analytics Calculator.
Counts and analyses stage transitions: forward, regression, re-entry, terminal.
"""
from __future__ import annotations
from typing import List, Dict, Optional

from app.domain.journey.models import JourneyState, JourneyStageTransition, TransitionType
from app.domain.journey.analytics.models import TransitionAnalytics, TransitionSummaryMetrics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class TransitionAnalyticsCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def _is_forward(self, from_stage: Optional[str], to_stage: str, journey_type_sequence: List[str]) -> bool:
        """Check if transition goes forward in the sequence."""
        if from_stage is None:
            return True  # initialization is forward
        if from_stage not in journey_type_sequence or to_stage not in journey_type_sequence:
            return False
        return journey_type_sequence.index(to_stage) > journey_type_sequence.index(from_stage)

    def calculate(
        self,
        transitions: List[JourneyStageTransition],
        journey_states: List[JourneyState],
        terminal_stages: Optional[List[str]] = None,
    ) -> TransitionSummaryMetrics:
        """
        Aggregate all transitions into summary + per-transition-pair analytics.
        """
        terminal_set = set(terminal_stages or ["CLOSED_WON", "CLOSED_LOST", "INACTIVE"])
        total = len(transitions)

        # Group by (from_stage, to_stage)
        pair_transitions: Dict[tuple, List[JourneyStageTransition]] = {}
        journey_ids_per_pair: Dict[tuple, set] = {}

        forward_count = 0
        regression_count = 0
        reentry_count = 0
        terminal_count = 0

        for t in transitions:
            from_s = t.from_stage.value if t.from_stage else None
            to_s = t.to_stage.value
            pair = (from_s, to_s)

            if pair not in pair_transitions:
                pair_transitions[pair] = []
                journey_ids_per_pair[pair] = set()
            pair_transitions[pair].append(t)
            journey_ids_per_pair[pair].add(str(t.journey_instance_id))

            tt = t.transition_type
            if tt == TransitionType.ADVANCE or tt == TransitionType.INITIALIZATION or tt == TransitionType.REACTIVATION:
                forward_count += 1
            elif tt == TransitionType.REGRESSION:
                regression_count += 1
                reentry_count += 1
            elif tt == TransitionType.LATERAL:
                reentry_count += 1
            if tt == TransitionType.COMPLETION or tt == TransitionType.CLOSURE or to_s in terminal_set:
                terminal_count += 1

        # Build per-pair analytics
        by_transition: List[TransitionAnalytics] = []
        for (from_s, to_s), pair_list in pair_transitions.items():
            pair_count = len(pair_list)
            is_reg = any(
                t.transition_type == TransitionType.REGRESSION for t in pair_list
            )
            is_reentry = from_s == to_s or is_reg
            is_fwd = not is_reg and from_s != to_s
            is_term = to_s in terminal_set

            by_transition.append(TransitionAnalytics(
                from_stage=from_s,
                to_stage=to_s,
                transition_count=pair_count,
                unique_journeys=len(journey_ids_per_pair[(from_s, to_s)]),
                transition_percentage=self._stats.safe_percentage(pair_count, total),
                average_time_to_transition_days=None,  # would need journey start as reference
                median_time_to_transition_days=None,
                is_forward=is_fwd,
                is_regression=is_reg,
                is_reentry=is_reentry,
                is_terminal=is_term,
            ))

        return TransitionSummaryMetrics(
            total_transitions=total,
            forward_transition_count=forward_count,
            regression_transition_count=regression_count,
            same_stage_reentry_count=reentry_count,
            terminal_transition_count=terminal_count,
            by_transition=by_transition,
        )

default_transition_calculator: TransitionAnalyticsCalculator = TransitionAnalyticsCalculator()
