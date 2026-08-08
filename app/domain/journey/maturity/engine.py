"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Engine

Deterministic 11-Stage Pipeline orchestrating stage residency, multi-factor maturity,
momentum, stability, velocity, health, and historical observed probability evaluation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    default_journey_registry,
)
from app.domain.journey.exceptions import (
    JourneyDefinitionError,
    JourneyNotFoundError,
    WorkspaceIsolationError,
)
from app.domain.journey.maturity.cache import (
    IJourneyMaturityCache,
    InMemoryJourneyMaturityCache,
)
from app.domain.journey.maturity.calculators.health import (
    JourneyHealthCalculator,
    default_health_calculator,
)
from app.domain.journey.maturity.calculators.maturity import (
    JourneyMaturityCalculator,
    default_maturity_calculator,
)
from app.domain.journey.maturity.calculators.momentum import (
    JourneyMomentumCalculator,
    default_momentum_calculator,
)
from app.domain.journey.maturity.calculators.residency import (
    StageResidencyCalculator,
    default_residency_calculator,
)
from app.domain.journey.maturity.calculators.stability import (
    JourneyStabilityCalculator,
    default_stability_calculator,
)
from app.domain.journey.maturity.calculators.velocity import (
    StageVelocityCalculator,
    default_velocity_calculator,
)
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfiguration,
    JourneyMaturityConfigurationRegistry,
    default_maturity_config_registry,
)
from app.domain.journey.maturity.models import (
    JourneyMaturityDiagnostics,
    JourneyMaturityProvenance,
    JourneyMaturityResult,
    ObservedJourneyProbability,
)
from app.domain.journey.maturity.probability import (
    ObservedProbabilityCalculator,
    default_probability_calculator,
)
from app.domain.journey.maturity.repository import (
    JourneyMaturityReadRepository,
    JourneyMaturityWriteRepository,
    default_maturity_repository,
)
from app.domain.journey.maturity.validation import (
    JourneyMaturityValidator,
    default_maturity_validator,
)
from app.domain.journey.models import (
    JourneyDefinition,
    JourneyStageTransition,
    JourneyState,
)
from app.domain.journey.repository import (
    JourneyReadRepository,
    default_journey_repository,
)


class JourneyMaturityEngine:
    """
    Orchestrates the 11-stage deterministic journey maturity and descriptive intelligence pipeline.
    """

    def __init__(
        self,
        journey_repo: Optional[JourneyReadRepository] = None,
        maturity_repo: Optional[Union[JourneyMaturityReadRepository, JourneyMaturityWriteRepository]] = None,
        journey_registry: Optional[JourneyDefinitionRegistry] = None,
        config_registry: Optional[JourneyMaturityConfigurationRegistry] = None,
        probability_calculator: Optional[ObservedProbabilityCalculator] = None,
        validator: Optional[JourneyMaturityValidator] = None,
        cache: Optional[IJourneyMaturityCache] = None,
    ) -> None:
        self._journey_repo = journey_repo or default_journey_repository
        self._maturity_repo = maturity_repo or default_maturity_repository
        self._journey_registry = journey_registry or default_journey_registry
        self._config_registry = config_registry or default_maturity_config_registry
        self._prob_calculator = probability_calculator or default_probability_calculator
        self._validator = validator or default_maturity_validator
        self._cache = cache or InMemoryJourneyMaturityCache()

    def calculate_maturity(
        self,
        journey_id: Union[uuid.UUID, str],
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
        configuration_version: Optional[str] = None,
        cohort_filters: Optional[Dict[str, Any]] = None,
        evaluated_at: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> JourneyMaturityResult:
        """
        Execute the 11-stage deterministic pipeline to calculate complete maturity result.
        """
        t0 = time.perf_counter()
        timings: Dict[str, float] = {}
        warnings: List[str] = []
        now = evaluated_at or datetime.now(timezone.utc)
        j_uuid = uuid.UUID(str(journey_id))

        # Check cache if allowed
        if use_cache:
            cached = self._cache.get(j_uuid)
            if cached is not None:
                if workspace_id and str(cached.workspace_id) != str(workspace_id):
                    raise WorkspaceIsolationError(
                        expected_workspace=str(workspace_id),
                        actual_workspace=str(cached.workspace_id),
                    )
                return cached

        # Stage 1: Load Journey State
        s1_t0 = time.perf_counter()
        journey_state = self._stage_1_load_state(j_uuid, workspace_id)
        timings["stage_1_load_state_ms"] = (time.perf_counter() - s1_t0) * 1000

        # Stage 2: Load Journey History
        s2_t0 = time.perf_counter()
        transitions = self._stage_2_load_history(j_uuid)
        timings["stage_2_load_history_ms"] = (time.perf_counter() - s2_t0) * 1000

        # Stage 3: Load Journey Definition & Configuration
        s3_t0 = time.perf_counter()
        definition, config = self._stage_3_load_definition(journey_state, configuration_version)
        timings["stage_3_load_definition_ms"] = (time.perf_counter() - s3_t0) * 1000

        # Build provenance
        calc_id = uuid.uuid4()
        prov = JourneyMaturityProvenance(
            calculation_id=calc_id,
            journey_id=j_uuid,
            workspace_id=journey_state.workspace_id or uuid.uuid4(),
            entity_id=journey_state.entity_id,
            engine_version="1.0.0",
            pipeline_version="2.4.3",
            configuration_version=config.version,
            generated_at=now,
            source_modules=[
                "app.domain.journey.maturity.engine",
                "app.domain.journey.maturity.calculators",
            ],
            source_artifacts=[
                f"journey_state:{j_uuid}",
                f"transitions:{len(transitions)}",
            ],
            calculation_method="DETERMINISTIC_11_STAGE_PIPELINE",
        )

        # Stage 4: Calculate Stage Residency
        s4_t0 = time.perf_counter()
        all_residencies, current_residency = StageResidencyCalculator.calculate_residency(
            journey_state=journey_state,
            transitions=transitions,
            evaluated_at=now,
        )
        timings["stage_4_calculate_residency_ms"] = (time.perf_counter() - s4_t0) * 1000

        # Stage 5: Calculate Maturity
        s5_t0 = time.perf_counter()
        maturity = JourneyMaturityCalculator.calculate_maturity(
            journey_state=journey_state,
            journey_definition=definition,
            transitions=transitions,
            config=config,
            provenance=prov,
            evaluated_at=now,
        )
        timings["stage_5_calculate_maturity_ms"] = (time.perf_counter() - s5_t0) * 1000

        # Stage 6: Calculate Momentum
        s6_t0 = time.perf_counter()
        momentum = JourneyMomentumCalculator.calculate_momentum(
            journey_state=journey_state,
            transitions=transitions,
            evaluated_at=now,
        )
        timings["stage_6_calculate_momentum_ms"] = (time.perf_counter() - s6_t0) * 1000

        # Stage 7: Calculate Stability
        s7_t0 = time.perf_counter()
        stability = JourneyStabilityCalculator.calculate_stability(
            journey_state=journey_state,
            transitions=transitions,
            evaluated_at=now,
        )
        timings["stage_7_calculate_stability_ms"] = (time.perf_counter() - s7_t0) * 1000

        # Stage 8: Calculate Velocity
        s8_t0 = time.perf_counter()
        velocity = StageVelocityCalculator.calculate_velocity(
            journey_state=journey_state,
            residencies=all_residencies,
            transitions=transitions,
            evaluated_at=now,
        )
        timings["stage_8_calculate_velocity_ms"] = (time.perf_counter() - s8_t0) * 1000

        # Stage 9: Calculate Historical Observed Probability
        s9_t0 = time.perf_counter()
        observed_prob = self._stage_9_calculate_probability(
            journey_state=journey_state,
            definition=definition,
            config=config,
            cohort_filters=cohort_filters,
            provenance=prov,
        )
        timings["stage_9_calculate_probability_ms"] = (time.perf_counter() - s9_t0) * 1000

        # Compute descriptive structural health
        health = JourneyHealthCalculator.calculate_health(
            journey_state=journey_state,
            maturity=maturity,
            momentum=momentum,
            stability=stability,
            velocity=velocity,
            evaluated_at=now,
        )

        # Stage 10: Validate Results
        s10_t0 = time.perf_counter()
        total_time_ms = (time.perf_counter() - t0) * 1000
        diagnostics = JourneyMaturityDiagnostics(
            stage_timings=timings,
            total_execution_time_ms=round(total_time_ms, 2),
            evidence_count=sum(len(t.evidence) for t in transitions),
            transition_count=len(transitions),
            residency_count=len(all_residencies),
            rules_evaluated=len(config.stage_weights),
            rules_matched=1 if journey_state.current_stage in config.stage_weights else 0,
            warnings=warnings,
            validation_errors=[],
            probability_available=observed_prob.minimum_sample_met if observed_prob else False,
            probability_sample_size=observed_prob.sample_size if observed_prob else 0,
            calculation_version="2.4.3",
        )

        result = JourneyMaturityResult(
            journey_id=j_uuid,
            workspace_id=journey_state.workspace_id or uuid.uuid4(),
            entity_id=journey_state.entity_id,
            current_stage=journey_state.current_stage,
            journey_status=journey_state.status,
            maturity=maturity,
            momentum=momentum,
            stability=stability,
            velocity=velocity,
            stage_residency=all_residencies,
            current_residency=current_residency,
            observed_probability=observed_prob,
            health=health,
            diagnostics=diagnostics,
            provenance=prov,
            calculated_at=now,
        )

        self._validator.validate_maturity_result(result)
        timings["stage_10_validate_results_ms"] = (time.perf_counter() - s10_t0) * 1000

        # Stage 11: Generate Result, Cache & Persist
        if isinstance(self._maturity_repo, JourneyMaturityWriteRepository):
            self._maturity_repo.save_maturity_result(result)

        self._cache.set(j_uuid, result)
        return result

    # ── Pipeline Stage Methods ───────────────────────────────────────────────

    def _stage_1_load_state(
        self,
        journey_id: uuid.UUID,
        workspace_id: Optional[Union[uuid.UUID, str]],
    ) -> JourneyState:
        state = self._journey_repo.get_journey(journey_id)
        if state is None:
            raise JourneyNotFoundError(
                message=f"Journey with instance ID '{journey_id}' not found.",
                journey_id=journey_id,
            )
        if workspace_id is not None:
            self._validator.validate_workspace_isolation(state, workspace_id)
        return state

    def _stage_2_load_history(self, journey_id: uuid.UUID) -> List[JourneyStageTransition]:
        return self._journey_repo.get_transitions(journey_id)

    def _stage_3_load_definition(
        self,
        state: JourneyState,
        version: Optional[str] = None,
    ) -> tuple[JourneyDefinition, JourneyMaturityConfiguration]:
        definition = self._journey_registry.get(state.journey_definition_id)
        if definition is None:
            # Fallback by journey type
            definition = self._journey_registry.get_by_type(state.metadata.get("journey_type"))
        if definition is None:
            raise JourneyDefinitionError(
                message=f"Journey definition '{state.journey_definition_id}' not found.",
                definition_id=state.journey_definition_id,
            )

        config = self._config_registry.resolve(definition.journey_type, version)
        return definition, config

    def _stage_9_calculate_probability(
        self,
        journey_state: JourneyState,
        definition: JourneyDefinition,
        config: JourneyMaturityConfiguration,
        cohort_filters: Optional[Dict[str, Any]] = None,
        provenance: Optional[JourneyMaturityProvenance] = None,
    ) -> ObservedJourneyProbability:
        ws_id = journey_state.workspace_id
        if ws_id is None:
            return ObservedJourneyProbability(
                probability_id=uuid.uuid4(),
                value=None,
                status=ObservedProbabilityStatus.INSUFFICIENT_DATA,
                target_stage=None,
                target_outcome="CLOSED_WON",
                sample_size=0,
                success_count=0,
                failure_count=0,
                minimum_required_sample=config.minimum_sample_for_probability,
                minimum_sample_met=False,
                observation_window_days=config.observation_window_days,
                calculation_method="WILSON_SCORE_INTERVAL",
                confidence=0.0,
                limitations=["No workspace assigned to journey state."],
                provenance=provenance,
            )

        # Query all historical journeys in the exact same workspace
        historical_ws_journeys = self._journey_repo.query_by_workspace(ws_id)
        return self._prob_calculator.calculate_from_historical_cohort(
            workspace_id=ws_id,
            journey_type=definition.journey_type,
            current_stage=journey_state.current_stage,
            historical_journeys=historical_ws_journeys,
            target_outcome="CLOSED_WON",
            minimum_required_sample=config.minimum_sample_for_probability,
            observation_window_days=config.observation_window_days,
            cohort_filters=cohort_filters,
            provenance=provenance,
        )

    def get_latest_maturity(self, journey_id: Union[uuid.UUID, str]) -> Optional[JourneyMaturityResult]:
        if isinstance(self._maturity_repo, JourneyMaturityReadRepository):
            return self._maturity_repo.get_latest_maturity(journey_id)
        return None

    def get_maturity_history(self, journey_id: Union[uuid.UUID, str]) -> List[JourneyMaturityResult]:
        if isinstance(self._maturity_repo, JourneyMaturityReadRepository):
            return self._maturity_repo.get_maturity_history(journey_id)
        return []


default_maturity_engine = JourneyMaturityEngine()
