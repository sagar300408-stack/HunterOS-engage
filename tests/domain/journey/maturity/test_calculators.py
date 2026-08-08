"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Calculator Unit Tests
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.definitions.industry.real_estate import build_real_estate_sales_journey
from app.domain.journey.maturity.calculators.health import JourneyHealthCalculator
from app.domain.journey.maturity.calculators.maturity import JourneyMaturityCalculator
from app.domain.journey.maturity.calculators.momentum import JourneyMomentumCalculator
from app.domain.journey.maturity.calculators.residency import StageResidencyCalculator
from app.domain.journey.maturity.calculators.stability import JourneyStabilityCalculator
from app.domain.journey.maturity.calculators.velocity import StageVelocityCalculator
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfiguration,
    build_sales_maturity_configuration,
)
from app.domain.journey.maturity.models import (
    JourneyHealthState,
    JourneyMaturityLevel,
    JourneyMomentumState,
    JourneyStabilityLevel,
    StageVelocityState,
)
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyType,
    TransitionType,
)


def _make_sample_state(
    current_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD,
    status: JourneyStatus = JourneyStatus.ACTIVE,
    days_ago: float = 10.0,
    stage_days_ago: float = 5.0,
    stage_history: list[JourneyStageCode] | None = None,
) -> JourneyState:
    now = datetime.now(timezone.utc)
    started = now - timedelta(days=days_ago)
    entered = now - timedelta(days=stage_days_ago)
    history = stage_history or [current_stage]
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id="ws-calc-test",
        entity_type="CUSTOMER",
        entity_id="cust-101",
        journey_definition_id=uuid.uuid4(),
        journey_definition_version="1.0.0",
        current_stage=current_stage,
        status=status,
        stage_history=history,
        journey_started_at=started,
        stage_entered_at=entered,
    )


def _make_transition(
    from_stage: JourneyStageCode,
    to_stage: JourneyStageCode,
    trans_type: TransitionType = TransitionType.ADVANCE,
    confidence: float = 0.85,
    days_ago: float = 5.0,
) -> JourneyStageTransition:
    now = datetime.now(timezone.utc)
    ev = JourneyEvidence(
        evidence_id=uuid.uuid4(),
        evidence_type=EvidenceType.INTENT,
        source_id="msg-1",
        confidence=confidence,
    )
    return JourneyStageTransition(
        transition_id=uuid.uuid4(),
        journey_instance_id=uuid.uuid4(),
        from_stage=from_stage,
        to_stage=to_stage,
        transition_type=trans_type,
        confidence=confidence,
        evidence=[ev],
        occurred_at=now - timedelta(days=days_ago),
    )


# ── 1. Stage Residency Calculator Tests ──────────────────────────────────────────


def test_stage_residency_single_stage():
    now = datetime.now(timezone.utc)
    state = _make_sample_state(days_ago=10.0, stage_days_ago=10.0)
    residencies, active = StageResidencyCalculator.calculate_residency(state, [], evaluated_at=now)

    assert len(residencies) == 1
    res = residencies[0]
    assert res.stage == JourneyStageCode.NEW_LEAD
    assert res.exited_at is None
    assert 9.9 <= res.duration_days <= 10.1
    assert res.reentry_count == 0
    assert active == res


def test_stage_residency_with_transitions():
    now = datetime.now(timezone.utc)
    state = _make_sample_state(
        current_stage=JourneyStageCode.QUALIFIED,
        days_ago=20.0,
        stage_days_ago=5.0,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED],
    )
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, days_ago=15.0)
    t2 = _make_transition(JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED, days_ago=5.0)

    residencies, active = StageResidencyCalculator.calculate_residency(state, [t1, t2], evaluated_at=now)

    assert len(residencies) == 3
    stage_map = {r.stage: r for r in residencies}
    assert stage_map[JourneyStageCode.NEW_LEAD].exited_at is not None
    assert 4.5 <= stage_map[JourneyStageCode.NEW_LEAD].duration_days <= 5.5
    assert stage_map[JourneyStageCode.INTERESTED].exited_at is not None
    assert 9.5 <= stage_map[JourneyStageCode.INTERESTED].duration_days <= 10.5
    assert stage_map[JourneyStageCode.QUALIFIED].exited_at is None
    assert 4.5 <= stage_map[JourneyStageCode.QUALIFIED].duration_days <= 5.5
    assert active.stage == JourneyStageCode.QUALIFIED


def test_stage_residency_reentry_tracking():
    now = datetime.now(timezone.utc)
    state = _make_sample_state(
        current_stage=JourneyStageCode.INTERESTED,
        days_ago=30.0,
        stage_days_ago=2.0,
        stage_history=[
            JourneyStageCode.NEW_LEAD,
            JourneyStageCode.INTERESTED,
            JourneyStageCode.QUALIFIED,
            JourneyStageCode.INTERESTED,
        ],
    )
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, days_ago=20.0)
    t2 = _make_transition(JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED, days_ago=10.0)
    t3 = _make_transition(
        JourneyStageCode.QUALIFIED,
        JourneyStageCode.INTERESTED,
        trans_type=TransitionType.REGRESSION,
        days_ago=2.0,
    )

    residencies, active = StageResidencyCalculator.calculate_residency(state, [t1, t2, t3], evaluated_at=now)
    assert active.stage == JourneyStageCode.INTERESTED
    assert active.reentry_count >= 1


# ── 2. Journey Maturity Calculator Tests ─────────────────────────────────────────


def test_maturity_initial_new_lead():
    defn = build_sales_journey_definition()
    state = _make_sample_state(current_stage=JourneyStageCode.NEW_LEAD, days_ago=1.0, stage_days_ago=1.0)
    maturity = JourneyMaturityCalculator.calculate_maturity(state, defn, [])

    assert maturity.maturity_level == JourneyMaturityLevel.INITIAL
    assert 0.0 <= maturity.maturity_score <= 0.15
    assert maturity.factors.stage_position_factor > 0.0
    assert maturity.factors.transition_history_factor == 0.0


def test_maturity_progressing_journey():
    defn = build_sales_journey_definition()
    state = _make_sample_state(
        current_stage=JourneyStageCode.NEGOTIATION,
        days_ago=30.0,
        stage_days_ago=5.0,
        stage_history=[
            JourneyStageCode.NEW_LEAD,
            JourneyStageCode.INTERESTED,
            JourneyStageCode.QUALIFIED,
            JourneyStageCode.PROPOSAL,
            JourneyStageCode.NEGOTIATION,
        ],
    )
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, days_ago=25.0)
    t2 = _make_transition(JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED, days_ago=18.0)
    t3 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, days_ago=10.0)
    t4 = _make_transition(JourneyStageCode.PROPOSAL, JourneyStageCode.NEGOTIATION, days_ago=5.0)

    maturity = JourneyMaturityCalculator.calculate_maturity(state, defn, [t1, t2, t3, t4])
    assert maturity.maturity_score > 0.50
    assert maturity.maturity_level in (
        JourneyMaturityLevel.QUALIFIED,
        JourneyMaturityLevel.ADVANCED,
        JourneyMaturityLevel.LATE_STAGE,
        JourneyMaturityLevel.COMPLETED,
    )
    assert maturity.factors.stage_completion_factor > 0.3
    assert maturity.factors.progression_consistency_factor == 1.0


def test_maturity_completed_closed_won():
    defn = build_sales_journey_definition()
    state = _make_sample_state(
        current_stage=JourneyStageCode.CLOSED_WON,
        status=JourneyStatus.COMPLETED,
        days_ago=40.0,
        stage_days_ago=1.0,
    )
    maturity = JourneyMaturityCalculator.calculate_maturity(state, defn, [])
    assert maturity.maturity_score == 1.0
    assert maturity.maturity_level == JourneyMaturityLevel.COMPLETED


def test_maturity_closed_lost():
    defn = build_sales_journey_definition()
    state = _make_sample_state(
        current_stage=JourneyStageCode.CLOSED_LOST,
        status=JourneyStatus.LOST,
        days_ago=40.0,
        stage_days_ago=1.0,
    )
    maturity = JourneyMaturityCalculator.calculate_maturity(state, defn, [])
    assert maturity.maturity_score <= 0.40


# ── 3. Journey Momentum Calculator Tests ─────────────────────────────────────────


def test_momentum_advancing():
    state = _make_sample_state(current_stage=JourneyStageCode.PROPOSAL, days_ago=20.0, stage_days_ago=2.0)
    t1 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, trans_type=TransitionType.ADVANCE, days_ago=2.0)
    momentum = JourneyMomentumCalculator.calculate_momentum(state, [t1])

    assert momentum.state in (JourneyMomentumState.ADVANCING, JourneyMomentumState.STRONGLY_ADVANCING)
    assert momentum.momentum_score > 0.0
    assert momentum.recent_advancements_count >= 1


def test_momentum_regressing():
    state = _make_sample_state(current_stage=JourneyStageCode.QUALIFIED, days_ago=30.0, stage_days_ago=2.0)
    t1 = _make_transition(JourneyStageCode.PROPOSAL, JourneyStageCode.QUALIFIED, trans_type=TransitionType.REGRESSION, days_ago=2.0)
    momentum = JourneyMomentumCalculator.calculate_momentum(state, [t1])

    assert momentum.state == JourneyMomentumState.REGRESSING
    assert momentum.momentum_score < 0.0
    assert momentum.recent_regressions_count >= 1


def test_momentum_inactive():
    state = _make_sample_state(current_stage=JourneyStageCode.QUALIFIED, days_ago=100.0, stage_days_ago=70.0)
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=70.0)
    momentum = JourneyMomentumCalculator.calculate_momentum(state, [t1])

    assert momentum.state == JourneyMomentumState.INACTIVE
    assert momentum.momentum_score < 0.0


def test_momentum_terminal_stable():
    state = _make_sample_state(current_stage=JourneyStageCode.CLOSED_WON, status=JourneyStatus.COMPLETED)
    momentum = JourneyMomentumCalculator.calculate_momentum(state, [])
    assert momentum.state == JourneyMomentumState.STABLE
    assert momentum.momentum_score == 0.0


# ── 4. Journey Stability Calculator Tests ────────────────────────────────────────


def test_stability_high_linear_progress():
    state = _make_sample_state(
        current_stage=JourneyStageCode.PROPOSAL,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL],
    )
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=10.0)
    t2 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, days_ago=2.0)
    stability = JourneyStabilityCalculator.calculate_stability(state, [t1, t2])

    assert stability.stability_level in (JourneyStabilityLevel.STABLE, JourneyStabilityLevel.VERY_STABLE)
    assert stability.stability_score >= 0.70
    assert stability.stage_reentry_count == 0


def test_stability_volatile_with_regressions_and_reentries():
    state = _make_sample_state(
        current_stage=JourneyStageCode.NEW_LEAD,
        stage_history=[
            JourneyStageCode.NEW_LEAD,
            JourneyStageCode.QUALIFIED,
            JourneyStageCode.NEW_LEAD,
            JourneyStageCode.QUALIFIED,
            JourneyStageCode.NEW_LEAD,
        ],
    )
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=20.0)
    t2 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.NEW_LEAD, trans_type=TransitionType.REGRESSION, days_ago=15.0)
    t3 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=10.0)
    t4 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.NEW_LEAD, trans_type=TransitionType.REGRESSION, days_ago=5.0)

    stability = JourneyStabilityCalculator.calculate_stability(state, [t1, t2, t3, t4])
    assert stability.stability_level in (JourneyStabilityLevel.UNSTABLE, JourneyStabilityLevel.HIGHLY_UNSTABLE)
    assert stability.stability_score < 0.60
    assert stability.stage_reentry_count >= 2


# ── 5. Stage Velocity Calculator Tests ──────────────────────────────────────────


def test_velocity_fast():
    state = _make_sample_state(current_stage=JourneyStageCode.BOOKING, days_ago=6.0, stage_days_ago=1.0)
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=5.0)
    t2 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, days_ago=3.0)
    t3 = _make_transition(JourneyStageCode.PROPOSAL, JourneyStageCode.BOOKING, days_ago=1.0)
    transitions = [t1, t2, t3]
    residencies, _ = StageResidencyCalculator.calculate_residency(state, transitions)

    vel = StageVelocityCalculator.calculate_velocity(state, residencies, transitions)
    assert vel.velocity_state == StageVelocityState.FAST
    assert vel.transitions_per_week >= 1.5


def test_velocity_stalled():
    state = _make_sample_state(current_stage=JourneyStageCode.QUALIFIED, days_ago=80.0, stage_days_ago=55.0)
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=55.0)
    transitions = [t1]
    residencies, _ = StageResidencyCalculator.calculate_residency(state, transitions)

    vel = StageVelocityCalculator.calculate_velocity(state, residencies, transitions)
    assert vel.velocity_state == StageVelocityState.STALLED
    assert vel.current_stage_duration_days >= 50.0


# ── 6. Journey Health Calculator Tests ───────────────────────────────────────────


def test_health_healthy_progressing():
    defn = build_sales_journey_definition()
    state = _make_sample_state(current_stage=JourneyStageCode.PROPOSAL, days_ago=15.0, stage_days_ago=2.0)
    t1 = _make_transition(JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, days_ago=10.0)
    t2 = _make_transition(JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, days_ago=2.0)
    transitions = [t1, t2]

    residencies, _ = StageResidencyCalculator.calculate_residency(state, transitions)
    maturity = JourneyMaturityCalculator.calculate_maturity(state, defn, transitions)
    momentum = JourneyMomentumCalculator.calculate_momentum(state, transitions)
    stability = JourneyStabilityCalculator.calculate_stability(state, transitions)
    velocity = StageVelocityCalculator.calculate_velocity(state, residencies, transitions)

    health = JourneyHealthCalculator.calculate_health(
        journey_state=state,
        maturity=maturity,
        momentum=momentum,
        stability=stability,
        velocity=velocity,
    )
    assert health.state in (JourneyHealthState.HEALTHY_PROGRESSING, JourneyHealthState.HEALTHY_STABLE)
    assert "Healthy" in health.summary or "advancing" in health.summary or "progressing" in health.summary.lower()
