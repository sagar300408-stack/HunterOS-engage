"""
Trend Analytics Calculator.
Time-series aggregation of journey metrics: daily, weekly, monthly.
No extrapolation. No forecasting. Historical only.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union

from app.domain.journey.models import JourneyState, JourneyStageTransition, JourneyStatus, TransitionType
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import JourneyTrendAnalytics, JourneyTrendPoint, AnalyticsObservationWindow, TrendGranularity
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyTrendCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def _get_period_label(self, dt: datetime, granularity: TrendGranularity) -> str:
        if granularity == TrendGranularity.DAILY:
            return dt.strftime("%Y-%m-%d")
        elif granularity == TrendGranularity.WEEKLY:
            # ISO week
            return dt.strftime("%G-W%V")
        else:  # MONTHLY
            return dt.strftime("%Y-%m")

    def _period_start(self, dt: datetime, granularity: TrendGranularity) -> datetime:
        if granularity == TrendGranularity.DAILY:
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == TrendGranularity.WEEKLY:
            # Monday of the week
            days_since_monday = dt.weekday()
            monday = dt - timedelta(days=days_since_monday)
            return monday.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def calculate(
        self,
        journey_states: List[JourneyState],
        transitions: List[JourneyStageTransition],
        maturity_results: List[JourneyMaturityResult],
        observation_window: AnalyticsObservationWindow,
        granularity: TrendGranularity = TrendGranularity.WEEKLY,
    ) -> JourneyTrendAnalytics:
        """
        Build time-series trend data points within the observation window.
        """
        start = observation_window.start_at
        end = observation_window.end_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Aggregate per period
        period_new_journeys: Dict[str, int] = {}
        period_active: Dict[str, int] = {}
        period_completed: Dict[str, int] = {}
        period_cancelled: Dict[str, int] = {}
        period_transitions: Dict[str, int] = {}
        period_forward: Dict[str, int] = {}
        period_regressions: Dict[str, int] = {}

        for j in journey_states:
            started = j.journey_started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if start <= started <= end:
                label = self._get_period_label(started, granularity)
                period_new_journeys[label] = period_new_journeys.get(label, 0) + 1

            if j.status == JourneyStatus.ACTIVE:
                label = self._get_period_label(started, granularity)
                period_active[label] = period_active.get(label, 0) + 1
            elif j.status in (JourneyStatus.COMPLETED, JourneyStatus.LOST):
                label = self._get_period_label(started, granularity)
                period_completed[label] = period_completed.get(label, 0) + 1
            elif j.status == JourneyStatus.CANCELLED:
                label = self._get_period_label(started, granularity)
                period_cancelled[label] = period_cancelled.get(label, 0) + 1

        for t in transitions:
            occurred = t.occurred_at
            if occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=timezone.utc)
            if start <= occurred <= end:
                label = self._get_period_label(occurred, granularity)
                period_transitions[label] = period_transitions.get(label, 0) + 1
                if t.transition_type == TransitionType.ADVANCE:
                    period_forward[label] = period_forward.get(label, 0) + 1
                elif t.transition_type == TransitionType.REGRESSION:
                    period_regressions[label] = period_regressions.get(label, 0) + 1

        # Build data points
        data_points: List[JourneyTrendPoint] = []
        all_labels: set = (
            set(period_new_journeys) | set(period_active) | set(period_completed) |
            set(period_cancelled) | set(period_transitions)
        )

        metric_dicts = {
            "new_journeys": period_new_journeys,
            "active_journeys": period_active,
            "completed_journeys": period_completed,
            "cancelled_journeys": period_cancelled,
            "stage_transitions": period_transitions,
            "forward_transitions": period_forward,
            "regressions": period_regressions,
        }

        for label in sorted(all_labels):
            for metric, d in metric_dicts.items():
                val = d.get(label, 0)
                # Use label as timestamp (approximate period start)
                try:
                    if granularity == TrendGranularity.DAILY:
                        ts = datetime.strptime(label, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    elif granularity == TrendGranularity.WEEKLY:
                        # Parse ISO week
                        ts = datetime.strptime(label + "-1", "%G-W%V-%u").replace(tzinfo=timezone.utc)
                    else:
                        ts = datetime.strptime(label + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    ts = datetime.now(timezone.utc)

                data_points.append(JourneyTrendPoint(
                    timestamp=ts,
                    period_label=label,
                    metric=metric,
                    value=float(val),
                    sample_size=val,
                ))

        metrics_tracked = list(metric_dicts.keys())

        return JourneyTrendAnalytics(
            granularity=granularity,
            observation_window=observation_window,
            metrics=metrics_tracked,
            data_points=sorted(data_points, key=lambda p: (p.period_label, p.metric)),
            total_periods=len(all_labels),
        )

default_trend_calculator: JourneyTrendCalculator = JourneyTrendCalculator()
