"""
Progression Pattern Analytics Calculator.
Classifies observed journey progression patterns from historical transitions.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.domain.journey.models import JourneyState, JourneyStatus, TransitionType
from app.domain.journey.analytics.models import ProgressionPatternAnalytics, ProgressionPattern
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class ProgressionPatternCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def _classify_pattern(self, j: JourneyState) -> ProgressionPattern:
        """Classify a single journey's progression pattern from its transition history."""
        transitions = j.transitions
        if not transitions:
            return ProgressionPattern.INACTIVE

        advances = sum(1 for t in transitions if t.transition_type == TransitionType.ADVANCE)
        regressions = sum(1 for t in transitions if t.transition_type == TransitionType.REGRESSION)
        total = len(transitions)

        if j.status == JourneyStatus.INACTIVE or (total > 0 and advances == 0 and regressions == 0):
            return ProgressionPattern.INACTIVE

        regression_ratio = regressions / total if total > 0 else 0.0
        if regression_ratio > 0.4:
            return ProgressionPattern.REGRESSIVE
        if regression_ratio > 0.2:
            return ProgressionPattern.OSCILLATING
        if advances == 0:
            return ProgressionPattern.STALLED
        if advances >= 3:
            return ProgressionPattern.MULTI_STEP_PROGRESS
        return ProgressionPattern.STEADY_PROGRESS

    def calculate(
        self,
        journey_states: List[JourneyState],
        reference_time: Optional[datetime] = None,
    ) -> ProgressionPatternAnalytics:
        now = reference_time or datetime.now(timezone.utc)
        total = len(journey_states)

        fwd_counts = []
        reg_counts = []
        reentry_counts = []
        stage_change_counts = []
        age_days = []
        consistency_scores = []
        pattern_counts: Dict[str, int] = {p.value: 0 for p in ProgressionPattern}

        for j in journey_states:
            transitions = j.transitions
            fwd = sum(1 for t in transitions if t.transition_type == TransitionType.ADVANCE)
            reg = sum(1 for t in transitions if t.transition_type == TransitionType.REGRESSION)
            reentry = sum(1 for t in transitions if t.transition_type == TransitionType.LATERAL)
            stage_changes = len(set(s.value for s in j.stage_history))

            fwd_counts.append(float(fwd))
            reg_counts.append(float(reg))
            reentry_counts.append(float(reentry))
            stage_change_counts.append(float(stage_changes))

            start = j.journey_started_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            days = (now - start).total_seconds() / 86400.0
            age_days.append(max(0.0, days))

            total_t = len(transitions)
            consistency = (fwd / total_t) if total_t > 0 else 1.0
            consistency_scores.append(consistency)

            pattern = self._classify_pattern(j)
            pattern_counts[pattern.value] = pattern_counts.get(pattern.value, 0) + 1

        pcts = self._stats.distribution_percentages(pattern_counts, total)

        return ProgressionPatternAnalytics(
            sample_size=total,
            average_forward_transitions=self._stats.mean(fwd_counts),
            average_regressions=self._stats.mean(reg_counts),
            average_reentries=self._stats.mean(reentry_counts),
            average_stage_changes=self._stats.mean(stage_change_counts),
            average_journey_age_days=self._stats.mean(age_days),
            progression_consistency_score=self._stats.mean(consistency_scores),
            pattern_distribution={k: v for k, v in pattern_counts.items() if v > 0},
            pattern_percentages={k: v for k, v in pcts.items() if pattern_counts.get(k, 0) > 0},
        )

default_progression_calculator: ProgressionPatternCalculator = ProgressionPatternCalculator()
