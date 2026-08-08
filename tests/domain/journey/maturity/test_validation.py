"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Maturity Validation Unit Tests
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.exceptions import JourneyValidationError, WorkspaceIsolationError
from app.domain.journey.maturity.models import (
    JourneyHealth,
    JourneyHealthState,
    JourneyMaturity,
    JourneyMaturityDiagnostics,
    JourneyMaturityLevel,
    JourneyMaturityProvenance,
    JourneyMaturityResult,
    JourneyMomentum,
    JourneyMomentumState,
    JourneyStability,
    JourneyStabilityLevel,
    MaturityFactors,
    ObservedJourneyProbability,
    ObservedProbabilityStatus,
    ObservedProbabilityType,
    StageResidency,
    StageResidencyStatus,
    StageVelocity,
    StageVelocityState,
)
from app.domain.journey.maturity.validation import JourneyMaturityValidator
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
    JourneyType,
)


def _make_dummy_result(
    score: float = 0.5,
    momentum_score: float = 0.2,
    stability_score: float = 0.8,
    prob_value: float | None = 0.6,
    sample_size: int = 50,
    min_sample: int = 30,
) -> JourneyMaturityResult:
    now = datetime.now(timezone.utc)
    jid = uuid.uuid4()
    wid = uuid.uuid4()

    prob = (
        ObservedJourneyProbability(
            probability_id=uuid.uuid4(),
            value=prob_value,
            status=ObservedProbabilityStatus.CALCULATED if prob_value is not None else ObservedProbabilityStatus.INSUFFICIENT_DATA,
            probability_type=ObservedProbabilityType.HISTORICAL_OBSERVED,
            sample_size=sample_size,
            minimum_required_sample=min_sample,
            minimum_sample_met=sample_size >= min_sample,
        )
        if prob_value is not None
        else None
    )

    factors = MaturityFactors(
        stage_position_factor=0.5,
        stage_completion_factor=0.5,
        transition_history_factor=0.5,
        evidence_strength_factor=0.5,
        journey_age_factor=0.5,
        stage_stability_factor=0.5,
        progression_consistency_factor=0.5,
    )

    maturity = JourneyMaturity(
        maturity_score=score,
        maturity_level=JourneyMaturityLevel.QUALIFIED,
        current_stage=JourneyStageCode.QUALIFIED,
        stage_position=3,
        total_active_stages=9,
        completed_stage_count=2,
        journey_progress_ratio=0.33,
        stage_duration_days=5.0,
        journey_age_days=15.0,
        evidence_strength=0.8,
        calculated_at=now,
        factors=factors,
        provenance=JourneyMaturityProvenance(
            calculation_id=uuid.uuid4(),
            journey_id=jid,
            workspace_id=wid,
            entity_id="cust-1",
            engine_version="1.0.0",
            pipeline_version="1.0.0",
            configuration_version="sales-v1",
            generated_at=now,
            source_modules=["validation"],
            source_artifacts=[],
            calculation_method="test",
        ),
    )

    residency = StageResidency(
        residency_id=uuid.uuid4(),
        stage=JourneyStageCode.QUALIFIED,
        entered_at=now,
        exited_at=None,
        duration_days=5.0,
        transition_count=1,
        reentry_count=0,
        evidence_count=2,
        confidence=0.9,
        status=StageResidencyStatus.ACTIVE,
    )

    return JourneyMaturityResult(
        journey_id=jid,
        workspace_id=wid,
        entity_id="cust-1",
        current_stage=JourneyStageCode.QUALIFIED,
        journey_status=JourneyStatus.ACTIVE,
        maturity=maturity,
        momentum=JourneyMomentum(
            state=JourneyMomentumState.ADVANCING,
            momentum_score=momentum_score,
            recent_advancements_count=1,
            recent_regressions_count=0,
            days_since_last_transition=2.0,
            transition_frequency_per_week=1.0,
            description="Advancing",
            calculated_at=now,
        ),
        stability=JourneyStability(
            stability_score=stability_score,
            stability_level=JourneyStabilityLevel.STABLE,
            current_stage_duration_days=5.0,
            stage_reentry_count=0,
            stage_transition_count=2,
            supporting_evidence_count=2,
            conflicting_evidence_count=0,
            calculated_at=now,
        ),
        velocity=StageVelocity(
            transitions_per_day=0.2,
            transitions_per_week=1.4,
            average_stage_duration_days=5.0,
            current_stage_duration_days=5.0,
            historical_average_duration_days=5.0,
            velocity_state=StageVelocityState.NORMAL,
            calculated_at=now,
        ),
        stage_residency=[residency],
        current_residency=residency,
        observed_probability=prob,
        health=JourneyHealth(
            state=JourneyHealthState.HEALTHY_PROGRESSING,
            summary="Healthy",
        ),
        diagnostics=JourneyMaturityDiagnostics(
            stage_timings={},
            total_execution_time_ms=1.2,
            evidence_count=2,
            transition_count=2,
            residency_count=1,
            rules_evaluated=5,
            rules_matched=2,
            warnings=[],
            validation_errors=[],
            probability_available=prob is not None,
            probability_sample_size=sample_size,
            calculation_version="1.0.0",
        ),
        provenance=maturity.provenance,
        calculated_at=now,
    )


def test_validate_workspace_isolation_matching():
    ws_id = uuid.uuid4()
    state = JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=ws_id,
        entity_type="CUSTOMER",
        entity_id="cust-1",
        journey_definition_id=uuid.uuid4(),
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD],
    )
    errors = JourneyMaturityValidator.validate_workspace_isolation(state, ws_id)
    assert errors == []


def test_validate_workspace_isolation_mismatch_raises():
    ws1 = uuid.uuid4()
    ws2 = uuid.uuid4()
    state = JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=ws1,
        entity_type="CUSTOMER",
        entity_id="cust-1",
        journey_definition_id=uuid.uuid4(),
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD],
    )
    with pytest.raises(WorkspaceIsolationError):
        JourneyMaturityValidator.validate_workspace_isolation(state, ws2)


def test_validate_definition_compatibility_matching():
    defn = build_sales_journey_definition()
    state = JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        entity_type="CUSTOMER",
        entity_id="cust-1",
        journey_definition_id=defn.journey_id,
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.QUALIFIED,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED],
    )
    errors = JourneyMaturityValidator.validate_definition_compatibility(state, defn)
    assert errors == []


def test_validate_maturity_result_valid():
    res = _make_dummy_result(score=0.75, momentum_score=0.5, stability_score=0.9, prob_value=0.6, sample_size=50)
    errors = JourneyMaturityValidator.validate_maturity_result(res)
    assert errors == []


def test_validate_maturity_result_small_sample_violation_raises():
    res = _make_dummy_result(score=0.75, momentum_score=0.5, stability_score=0.9, prob_value=0.6, sample_size=10, min_sample=30)
    with pytest.raises(JourneyValidationError) as exc:
        JourneyMaturityValidator.validate_maturity_result(res)
    assert "Small-sample violation" in str(exc.value)
