"""
Cohort Analytics Calculator.
Filters journeys by explicit cohort definitions and computes cohort metrics.
Comparison is purely descriptive. No recommendations.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.models import JourneyState, JourneyStatus
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.analytics.models import JourneyCohortDefinition, JourneyCohortMetrics, JourneyCohortComparison, AnalyticsObservationWindow
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine, default_stats_engine

class JourneyCohortCalculator:
    def __init__(self, stats: DescriptiveStatisticsEngine = default_stats_engine) -> None:
        self._stats = stats

    def _filter_journeys(
        self,
        journey_states: List[JourneyState],
        cohort: JourneyCohortDefinition,
    ) -> List[JourneyState]:
        """
        Filter journey states matching the cohort definition within the same workspace.
        """
        ws = str(cohort.workspace_id)
        filtered = [j for j in journey_states if str(j.workspace_id) == ws]

        if cohort.journey_type:
            filtered = [j for j in filtered if j.metadata.get("journey_type") == cohort.journey_type]
        if cohort.journey_definition_id:
            filtered = [j for j in filtered if str(j.journey_definition_id) == cohort.journey_definition_id]
        if cohort.stage:
            filtered = [j for j in filtered if j.current_stage.value == cohort.stage]
        if cohort.journey_status:
            filtered = [j for j in filtered if j.status.value == cohort.journey_status]
        if cohort.time_window:
            w = cohort.time_window
            filtered = [
                j for j in filtered
                if w.start_at <= j.journey_started_at.replace(tzinfo=timezone.utc if j.journey_started_at.tzinfo is None else j.journey_started_at.tzinfo) <= w.end_at
            ]
        return filtered

    def calculate_cohort_metrics(
        self,
        cohort: JourneyCohortDefinition,
        journey_states: List[JourneyState],
        maturity_results: List[JourneyMaturityResult],
        reference_time: Optional[datetime] = None,
        minimum_outcome_sample: int = 30,
    ) -> JourneyCohortMetrics:
        now = reference_time or datetime.now(timezone.utc)
        filtered = self._filter_journeys(journey_states, cohort)
        mat_by_id = {str(mr.journey_id): mr for mr in maturity_results}

        durations = []
        for j in filtered:
            start = j.journey_started_at.replace(
                tzinfo=timezone.utc if j.journey_started_at.tzinfo is None else j.journey_started_at.tzinfo
            )
            days = (now - start).total_seconds() / 86400.0
            durations.append(max(0.0, days))

        mat_scores = []
        stage_dist: Dict[str, int] = {}
        mom_dist: Dict[str, int] = {}
        stab_dist: Dict[str, int] = {}
        health_dist: Dict[str, int] = {}
        transition_counts = []

        for j in filtered:
            sc = j.current_stage.value
            stage_dist[sc] = stage_dist.get(sc, 0) + 1
            transition_counts.append(len(j.transitions))
            mr = mat_by_id.get(str(j.journey_instance_id))
            if mr:
                mat_scores.append(mr.maturity.maturity_score)
                ms = mr.momentum.state.value
                mom_dist[ms] = mom_dist.get(ms, 0) + 1
                sl = mr.stability.stability_level.value
                stab_dist[sl] = stab_dist.get(sl, 0) + 1
                hs = mr.health.state.value
                health_dist[hs] = health_dist.get(hs, 0) + 1

        avg_transitions = self._stats.mean([float(t) for t in transition_counts])

        # Historical outcome rate
        terminal = [
            j for j in filtered
            if j.status in (JourneyStatus.COMPLETED, JourneyStatus.LOST, JourneyStatus.CANCELLED)
            or j.current_stage.value in ("CLOSED_WON", "CLOSED_LOST")
        ]
        outcome_rate = None
        if len(terminal) >= minimum_outcome_sample:
            successes = sum(1 for j in terminal if j.current_stage.value == "CLOSED_WON" or j.status == JourneyStatus.COMPLETED)
            outcome_rate = self._stats.safe_ratio(float(successes), float(len(terminal)))

        return JourneyCohortMetrics(
            cohort=cohort,
            journey_count=len(filtered),
            average_duration_days=self._stats.mean(durations),
            median_duration_days=self._stats.median(durations),
            average_maturity_score=self._stats.mean(mat_scores),
            stage_distribution=stage_dist,
            momentum_distribution=mom_dist,
            stability_distribution=stab_dist,
            health_distribution=health_dist,
            transition_rate=avg_transitions,
            historical_outcome_rate=outcome_rate,
        )

    def compare_cohorts(
        self,
        cohorts: List[JourneyCohortDefinition],
        journey_states: List[JourneyState],
        maturity_results: List[JourneyMaturityResult],
        observation_window: AnalyticsObservationWindow,
        workspace_id: Union[uuid.UUID, str],
    ) -> JourneyCohortComparison:
        """
        Compare multiple cohorts. All cohorts must be within the same workspace.
        No recommendations generated.
        """
        ws = str(workspace_id)
        # Workspace isolation: all cohorts must match
        for c in cohorts:
            if str(c.workspace_id) != ws:
                raise ValueError(
                    f"Cohort workspace mismatch: cohort {c.cohort_id} belongs to {c.workspace_id}, expected {ws}."
                )

        cohort_metrics_list = [
            self.calculate_cohort_metrics(c, journey_states, maturity_results)
            for c in cohorts
        ]

        notes = [f"Descriptive comparison of {len(cohorts)} cohorts within workspace {ws}."]
        if len(cohorts) < 2:
            notes.append("Only one cohort provided; no comparison possible.")

        return JourneyCohortComparison(
            comparison_id=uuid.uuid4(),
            workspace_id=workspace_id,
            cohort_metrics=cohort_metrics_list,
            generated_at=datetime.now(timezone.utc),
            observation_window=observation_window,
            comparison_notes=notes,
        )

default_cohort_calculator: JourneyCohortCalculator = JourneyCohortCalculator()
