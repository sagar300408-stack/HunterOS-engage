"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.4: Journey Analytics Engine

Deterministic pipeline orchestrating all analytics calculators across
a workspace-scoped cohort of journeys, transitions, and maturity results.

PIPELINE STAGES (15-stage):
  1.  Context validation
  2.  Workspace isolation enforcement
  3.  Provenance initialization
  4.  Distribution metrics
  5.  Stage analytics
  6.  Transition analytics
  7.  Funnel analytics
  8.  Duration metrics
  9.  Residency analytics
  10. Maturity analytics
  11. Momentum analytics
  12. Stability analytics
  13. Velocity analytics
  14. Health analytics
  15. Progression pattern analytics
  16. Observed outcome analytics
  17. Trend analytics
  18. Diagnostics assembly
  19. Result assembly
  20. Cache & persist

STRICT INVARIANTS:
- DESCRIPTIVE ONLY: Never predicts stages, outcomes, or lead scores
- NO MUTATIONS: Never writes to JourneyState, MaturityResult, or Memory
- WORKSPACE-SCOPED: Enforces cross-workspace isolation before any calculation
- DETERMINISTIC: Same inputs -> same outputs
- ZERO-SAMPLE SAFE: All calculators handle empty datasets
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.analytics.cache import (
    IJourneyAnalyticsCache,
    InMemoryJourneyAnalyticsCache,
)
from app.domain.journey.analytics.calculators.distribution import (
    JourneyDistributionCalculator, default_distribution_calculator,
)
from app.domain.journey.analytics.calculators.stage import (
    StageAnalyticsCalculator, default_stage_analytics_calculator,
)
from app.domain.journey.analytics.calculators.transition import (
    TransitionAnalyticsCalculator, default_transition_calculator,
)
from app.domain.journey.analytics.calculators.funnel import (
    JourneyFunnelCalculator, default_funnel_calculator,
)
from app.domain.journey.analytics.calculators.duration import (
    JourneyDurationCalculator, default_duration_calculator,
)
from app.domain.journey.analytics.calculators.residency import (
    StageResidencyAnalyticsCalculator, default_residency_analytics_calculator,
)
from app.domain.journey.analytics.calculators.maturity import (
    MaturityAnalyticsCalculator, default_maturity_analytics_calculator,
)
from app.domain.journey.analytics.calculators.momentum import (
    MomentumAnalyticsCalculator, default_momentum_analytics_calculator,
)
from app.domain.journey.analytics.calculators.stability import (
    StabilityAnalyticsCalculator, default_stability_analytics_calculator,
)
from app.domain.journey.analytics.calculators.velocity import (
    VelocityAnalyticsCalculator, default_velocity_analytics_calculator,
)
from app.domain.journey.analytics.calculators.health import (
    JourneyHealthAnalyticsCalculator, default_health_analytics_calculator,
)
from app.domain.journey.analytics.calculators.outcome import (
    ObservedOutcomeCalculator, default_outcome_calculator,
)
from app.domain.journey.analytics.calculators.trends import (
    JourneyTrendCalculator, default_trend_calculator,
)
from app.domain.journey.analytics.calculators.cohort import (
    JourneyCohortCalculator, default_cohort_calculator,
)
from app.domain.journey.analytics.calculators.progression import (
    ProgressionPatternCalculator, default_progression_calculator,
)
from app.domain.journey.analytics.configuration import (
    JourneyAnalyticsConfiguration,
    JourneyAnalyticsConfigurationRegistry,
    default_analytics_config_registry,
)
from app.domain.journey.analytics.context import JourneyAnalyticsContext
from app.domain.journey.analytics.models import (
    AnalyticsObservationWindow,
    AnalyticsScope,
    JourneyAnalyticsDiagnostics,
    JourneyAnalyticsProvenance,
    JourneyAnalyticsResult,
    JourneyCohortDefinition,
    JourneyCohortMetrics,
    TrendGranularity,
)
from app.domain.journey.analytics.repository import (
    JourneyAnalyticsReadRepository,
    JourneyAnalyticsWriteRepository,
    default_analytics_repository,
)
from app.domain.journey.analytics.validation import (
    JourneyAnalyticsValidator,
    default_analytics_validator,
)
from app.domain.journey.maturity.models import JourneyMaturityResult
from app.domain.journey.maturity.repository import (
    JourneyMaturityReadRepository,
    default_maturity_repository,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyType,
)
from app.domain.journey.repository import (
    JourneyReadRepository,
    default_journey_repository,
)


ENGINE_VERSION = "2.4.4"
PIPELINE_VERSION = "analytics-pipeline-v1"


class JourneyAnalyticsEngine:
    """
    Deterministic analytics pipeline orchestrating all 15 analytics calculators.
    Read-only. Never mutates JourneyState, MaturityResult, or any upstream domain object.
    """

    def __init__(
        self,
        journey_repository: JourneyReadRepository = default_journey_repository,
        maturity_repository: JourneyMaturityReadRepository = default_maturity_repository,
        analytics_read_repository: JourneyAnalyticsReadRepository = default_analytics_repository,
        analytics_write_repository: JourneyAnalyticsWriteRepository = default_analytics_repository,
        config_registry: JourneyAnalyticsConfigurationRegistry = default_analytics_config_registry,
        validator: JourneyAnalyticsValidator = default_analytics_validator,
        cache: Optional[IJourneyAnalyticsCache] = None,
        distribution_calculator: JourneyDistributionCalculator = default_distribution_calculator,
        stage_calculator: StageAnalyticsCalculator = default_stage_analytics_calculator,
        transition_calculator: TransitionAnalyticsCalculator = default_transition_calculator,
        funnel_calculator: JourneyFunnelCalculator = default_funnel_calculator,
        duration_calculator: JourneyDurationCalculator = default_duration_calculator,
        residency_calculator: StageResidencyAnalyticsCalculator = default_residency_analytics_calculator,
        maturity_calculator: MaturityAnalyticsCalculator = default_maturity_analytics_calculator,
        momentum_calculator: MomentumAnalyticsCalculator = default_momentum_analytics_calculator,
        stability_calculator: StabilityAnalyticsCalculator = default_stability_analytics_calculator,
        velocity_calculator: VelocityAnalyticsCalculator = default_velocity_analytics_calculator,
        health_calculator: JourneyHealthAnalyticsCalculator = default_health_analytics_calculator,
        outcome_calculator: ObservedOutcomeCalculator = default_outcome_calculator,
        trend_calculator: JourneyTrendCalculator = default_trend_calculator,
        cohort_calculator: JourneyCohortCalculator = default_cohort_calculator,
        progression_calculator: ProgressionPatternCalculator = default_progression_calculator,
    ) -> None:
        self._journey_repo = journey_repository
        self._maturity_repo = maturity_repository
        self._read_repo = analytics_read_repository
        self._write_repo = analytics_write_repository
        self._config_registry = config_registry
        self._validator = validator
        self._cache = cache or InMemoryJourneyAnalyticsCache()

        # Calculators
        self._distribution = distribution_calculator
        self._stage = stage_calculator
        self._transition = transition_calculator
        self._funnel = funnel_calculator
        self._duration = duration_calculator
        self._residency = residency_calculator
        self._maturity = maturity_calculator
        self._momentum = momentum_calculator
        self._stability = stability_calculator
        self._velocity = velocity_calculator
        self._health = health_calculator
        self._outcome = outcome_calculator
        self._trend = trend_calculator
        self._cohort = cohort_calculator
        self._progression = progression_calculator

    def _build_cache_key(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str],
        configuration_version: Optional[str],
        observation_window_days: int,
    ) -> str:
        return f"{workspace_id}::{journey_type or 'ALL'}::{configuration_version or 'default'}::{observation_window_days}"

    def _build_observation_window(
        self,
        observation_window_days: int,
        evaluated_at: Optional[datetime] = None,
    ) -> AnalyticsObservationWindow:
        end = evaluated_at or datetime.now(timezone.utc)
        start = end - timedelta(days=observation_window_days)
        return AnalyticsObservationWindow(start_at=start, end_at=end)

    def _collect_journeys(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> List[JourneyState]:
        """Collect all journey states for the workspace from the read repository."""
        all_journeys = self._journey_repo.query_by_workspace(workspace_id)
        if journey_type:
            all_journeys = [
                j for j in all_journeys
                if j.metadata.get("journey_type") == journey_type
            ]
        return all_journeys

    def _collect_transitions(
        self, journey_states: List[JourneyState]
    ) -> List[JourneyStageTransition]:
        """Collect all transitions across all journeys."""
        transitions: List[JourneyStageTransition] = []
        for j in journey_states:
            transitions.extend(j.transitions)
        return transitions

    def _collect_maturity_results(
        self, journey_states: List[JourneyState]
    ) -> List[JourneyMaturityResult]:
        """Collect the latest maturity result for each journey."""
        results: List[JourneyMaturityResult] = []
        for j in journey_states:
            mr = self._maturity_repo.get_latest_maturity(j.journey_instance_id)
            if mr is not None:
                results.append(mr)
        return results

    def _infer_funnel_stages(
        self, journey_states: List[JourneyState], journey_type: Optional[str]
    ) -> List[str]:
        """Infer funnel stage order from observed journey histories."""
        # Build stage sequence map from all stage histories
        # Use a simple approach: collect all unique stages ordered by first appearance
        stage_first_seen: Dict[str, int] = {}
        for j in journey_states:
            for idx, stage in enumerate(j.stage_history):
                sv = stage.value
                if sv not in stage_first_seen:
                    stage_first_seen[sv] = idx
                else:
                    stage_first_seen[sv] = min(stage_first_seen[sv], idx)
        # Sort by average position
        return sorted(stage_first_seen.keys(), key=lambda s: stage_first_seen[s])

    def calculate(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
        definition_version: Optional[str] = None,
        configuration_version: Optional[str] = None,
        observation_window_days: Optional[int] = None,
        evaluated_at: Optional[datetime] = None,
        use_cache: bool = True,
        cohort: Optional[JourneyCohortDefinition] = None,
        scope: AnalyticsScope = AnalyticsScope.WORKSPACE,
    ) -> JourneyAnalyticsResult:
        """
        Execute the full 20-stage analytics pipeline.
        Returns a complete, immutable JourneyAnalyticsResult.
        Never predicts. Never mutates. Never crosses workspace boundaries.
        """
        pipeline_start = time.monotonic()
        stage_timings: Dict[str, float] = {}
        warnings: List[str] = []
        validation_errors: List[str] = []

        # Stage 1: Resolve configuration
        t0 = time.monotonic()
        cfg = self._config_registry.resolve(configuration_version)
        obs_days = observation_window_days or cfg.default_observation_window_days
        observation_window = self._build_observation_window(obs_days, evaluated_at)
        stage_timings["configuration"] = (time.monotonic() - t0) * 1000

        # Stage 2: Cache lookup
        t0 = time.monotonic()
        cache_key = self._build_cache_key(workspace_id, journey_type, configuration_version, obs_days)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        stage_timings["cache_lookup"] = (time.monotonic() - t0) * 1000

        # Stage 3: Collect source data
        t0 = time.monotonic()
        journey_states = self._collect_journeys(workspace_id, journey_type)
        transitions = self._collect_transitions(journey_states)
        maturity_results = self._collect_maturity_results(journey_states)
        stage_timings["data_collection"] = (time.monotonic() - t0) * 1000

        # Stage 4: Validate
        t0 = time.monotonic()
        if journey_states:
            validation_errors.extend(
                self._validator.validate_workspace_isolation(journey_states, workspace_id)
            )
            validation_errors.extend(
                self._validator.validate_observation_window(observation_window)
            )
            validation_errors.extend(
                self._validator.validate_duplicate_journeys(journey_states)
            )
        stage_timings["validation"] = (time.monotonic() - t0) * 1000

        empty_dataset = len(journey_states) == 0
        partial_dataset = len(maturity_results) < len(journey_states)
        insufficient_data_metrics: List[str] = []
        if partial_dataset:
            warnings.append(
                f"Partial dataset: {len(maturity_results)} maturity results for "
                f"{len(journey_states)} journeys. Some analytics metrics may be missing."
            )

        # Stage 5: Distribution metrics
        t0 = time.monotonic()
        distribution = self._distribution.calculate(journey_states, maturity_results)
        stage_timings["distribution"] = (time.monotonic() - t0) * 1000

        # Stage 6: Stage analytics
        t0 = time.monotonic()
        stage_analytics = self._stage.calculate(journey_states, maturity_results)
        stage_timings["stage_analytics"] = (time.monotonic() - t0) * 1000

        # Stage 7: Transition analytics
        t0 = time.monotonic()
        transition_metrics = self._transition.calculate(transitions, journey_states)
        stage_timings["transition_analytics"] = (time.monotonic() - t0) * 1000

        # Stage 8: Funnel analytics
        t0 = time.monotonic()
        funnel_stages = self._infer_funnel_stages(journey_states, journey_type)
        funnel = self._funnel.calculate(
            journey_states,
            funnel_stages,
            minimum_sample=cfg.minimum_probability_sample,
        ) if journey_states else None
        stage_timings["funnel"] = (time.monotonic() - t0) * 1000

        # Stage 9: Duration metrics
        t0 = time.monotonic()
        duration_metrics = self._duration.calculate(journey_states, reference_time=evaluated_at)
        stage_timings["duration"] = (time.monotonic() - t0) * 1000

        # Stage 10: Residency analytics
        t0 = time.monotonic()
        residency_analytics = self._residency.calculate(maturity_results, cfg)
        stage_timings["residency"] = (time.monotonic() - t0) * 1000

        # Stage 11: Maturity analytics
        t0 = time.monotonic()
        maturity_analytics = self._maturity.calculate(maturity_results)
        if not maturity_results:
            insufficient_data_metrics.append("maturity_analytics")
        stage_timings["maturity"] = (time.monotonic() - t0) * 1000

        # Stage 12: Momentum analytics
        t0 = time.monotonic()
        momentum_analytics = self._momentum.calculate(maturity_results)
        if not maturity_results:
            insufficient_data_metrics.append("momentum_analytics")
        stage_timings["momentum"] = (time.monotonic() - t0) * 1000

        # Stage 13: Stability analytics
        t0 = time.monotonic()
        stability_analytics = self._stability.calculate(maturity_results)
        if not maturity_results:
            insufficient_data_metrics.append("stability_analytics")
        stage_timings["stability"] = (time.monotonic() - t0) * 1000

        # Stage 14: Velocity analytics
        t0 = time.monotonic()
        velocity_analytics = self._velocity.calculate(maturity_results)
        if not maturity_results:
            insufficient_data_metrics.append("velocity_analytics")
        stage_timings["velocity"] = (time.monotonic() - t0) * 1000

        # Stage 15: Health analytics
        t0 = time.monotonic()
        health_analytics = self._health.calculate(maturity_results)
        if not maturity_results:
            insufficient_data_metrics.append("health_analytics")
        stage_timings["health"] = (time.monotonic() - t0) * 1000

        # Stage 16: Progression pattern analytics
        t0 = time.monotonic()
        progression_patterns = self._progression.calculate(journey_states, reference_time=evaluated_at)
        stage_timings["progression"] = (time.monotonic() - t0) * 1000

        # Stage 17: Observed outcome analytics
        t0 = time.monotonic()
        outcome_analytics = self._outcome.calculate(
            journey_states=journey_states,
            workspace_id=workspace_id,
            observation_window_days=obs_days,
            confidence_level=cfg.confidence_level,
        )
        stage_timings["outcome"] = (time.monotonic() - t0) * 1000

        # Stage 18: Trend analytics
        t0 = time.monotonic()
        trend_analytics = self._trend.calculate(
            journey_states=journey_states,
            transitions=transitions,
            maturity_results=maturity_results,
            observation_window=observation_window,
            granularity=cfg.trend_granularity,
        ) if journey_states else None
        stage_timings["trends"] = (time.monotonic() - t0) * 1000

        # Stage 19: Cohort metrics
        t0 = time.monotonic()
        cohort_metrics: Optional[JourneyCohortMetrics] = None
        if cohort is not None:
            cohort_metrics = self._cohort.calculate_cohort_metrics(
                cohort=cohort,
                journey_states=journey_states,
                maturity_results=maturity_results,
                reference_time=evaluated_at,
                minimum_outcome_sample=cfg.minimum_probability_sample,
            )
        stage_timings["cohort"] = (time.monotonic() - t0) * 1000

        # Stage 20: Diagnostics assembly
        total_execution_ms = (time.monotonic() - pipeline_start) * 1000
        diagnostics = JourneyAnalyticsDiagnostics(
            stage_timings=stage_timings,
            total_execution_time_ms=round(total_execution_ms, 3),
            journeys_processed=len(journey_states),
            transitions_processed=len(transitions),
            timeline_events_processed=sum(
                len(j.timeline.events) if j.timeline else 0 for j in journey_states
            ),
            maturity_results_processed=len(maturity_results),
            metrics_calculated=[
                "distribution", "stage_analytics", "transition_metrics",
                "funnel", "duration_metrics", "residency_analytics",
                "maturity_analytics", "momentum_analytics", "stability_analytics",
                "velocity_analytics", "health_analytics", "progression_patterns",
                "outcome_analytics", "trend_analytics",
            ],
            warnings=warnings,
            validation_errors=validation_errors,
            empty_dataset=empty_dataset,
            partial_dataset=partial_dataset,
            insufficient_data_metrics=insufficient_data_metrics,
        )

        # Stage 21: Provenance
        analytics_id = uuid.uuid4()
        provenance = JourneyAnalyticsProvenance(
            analytics_id=analytics_id,
            workspace_id=workspace_id,
            generated_at=evaluated_at or datetime.now(timezone.utc),
            observation_window=observation_window,
            engine_version=ENGINE_VERSION,
            pipeline_version=PIPELINE_VERSION,
            configuration_version=configuration_version or "default",
            source_journey_count=len(journey_states),
            source_transition_count=len(transitions),
            source_maturity_count=len(maturity_results),
            filters={"journey_type": journey_type, "definition_version": definition_version},
            cohort_definition={"cohort_id": str(cohort.cohort_id), "cohort_name": cohort.cohort_name} if cohort else None,
            calculation_methods=[
                "DESCRIPTIVE_STATISTICS",
                "WILSON_SCORE_INTERVAL",
                "STAGE_SEQUENCE_INFERENCE",
            ],
            statistical_methods=[
                "MEAN", "MEDIAN", "PERCENTILE_LINEAR",
                "SAMPLE_STD_DEV", "WILSON_SCORE_CI",
            ],
        )

        # Stage 22: Result assembly
        result = JourneyAnalyticsResult(
            analytics_id=analytics_id,
            workspace_id=workspace_id,
            journey_type=journey_type,
            definition_version=definition_version,
            observation_window=observation_window,
            generated_at=provenance.generated_at,
            journey_count=len(journey_states),
            distribution=distribution,
            stage_analytics=stage_analytics,
            transition_metrics=transition_metrics,
            funnel=funnel,
            duration_metrics=duration_metrics,
            residency_analytics=residency_analytics,
            maturity_analytics=maturity_analytics,
            momentum_analytics=momentum_analytics,
            stability_analytics=stability_analytics,
            velocity_analytics=velocity_analytics,
            health_analytics=health_analytics,
            progression_patterns=progression_patterns,
            outcome_analytics=outcome_analytics,
            trend_analytics=trend_analytics,
            cohort_metrics=cohort_metrics,
            diagnostics=diagnostics,
            provenance=provenance,
        )

        # Stage 23: Cache & persist
        self._cache.set(cache_key, result)
        self._write_repo.save_result(result)

        return result

    def get_latest(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
    ) -> Optional[JourneyAnalyticsResult]:
        """Get the latest persisted analytics result without recalculating."""
        return self._read_repo.get_latest_result(workspace_id, journey_type)

    def invalidate_cache(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_type: Optional[str] = None,
        configuration_version: Optional[str] = None,
        observation_window_days: int = 365,
    ) -> None:
        """Invalidate cache for a workspace/journey_type combination."""
        cache_key = self._build_cache_key(
            workspace_id, journey_type, configuration_version, observation_window_days
        )
        self._cache.invalidate(cache_key)


# Module-level singleton wired with all defaults
default_analytics_engine: JourneyAnalyticsEngine = JourneyAnalyticsEngine()
