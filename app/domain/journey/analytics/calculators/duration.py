"""
Journey Duration Analytics Calculator.
Calculates duration statistics across active, completed, and cancelled journeys.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.journey.models import JourneyState, JourneyStatus
from app.domain.journey.analytics.models import JourneyDurationMetrics
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyDurationCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def calculate(
        self,
        journey_states: List[JourneyState],
        reference_time: Optional[datetime] = None,
    ) -> JourneyDurationMetrics:
        now = reference_time or datetime.now(timezone.utc)

        all_durations = []
        active_durations = []
        completed_durations = []
        cancelled_durations = []

        for j in journey_states:
            start = j.journey_started_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            end = now
            if j.status in (JourneyStatus.COMPLETED, JourneyStatus.LOST):
                end = j.last_transition_at or now
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
            elif j.status == JourneyStatus.CANCELLED:
                end = j.last_transition_at or now
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

            days = max(0.0, (end - start).total_seconds() / 86400.0)
            all_durations.append(days)

            if j.status == JourneyStatus.ACTIVE:
                active_durations.append(days)
            elif j.status in (JourneyStatus.COMPLETED, JourneyStatus.LOST):
                completed_durations.append(days)
            elif j.status == JourneyStatus.CANCELLED:
                cancelled_durations.append(days)

        return JourneyDurationMetrics(
            total_sample_size=len(all_durations),
            average_duration_days=self._stats.mean(all_durations),
            median_duration_days=self._stats.median(all_durations),
            minimum_duration_days=self._stats.minimum(all_durations),
            maximum_duration_days=self._stats.maximum(all_durations),
            p25_duration_days=self._stats.percentile(all_durations, 25) if len(all_durations) >= 4 else None,
            p75_duration_days=self._stats.percentile(all_durations, 75) if len(all_durations) >= 4 else None,
            active_average_days=self._stats.mean(active_durations),
            completed_average_days=self._stats.mean(completed_durations),
            cancelled_average_days=self._stats.mean(cancelled_durations),
        )

default_duration_calculator: JourneyDurationCalculator = JourneyDurationCalculator()
