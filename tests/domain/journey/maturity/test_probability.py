"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Observed Probability Calculator Unit Tests
"""

from __future__ import annotations

import uuid
import pytest

from app.domain.journey.maturity.models import (
    ObservedJourneyProbability,
    ObservedProbabilityStatus,
    ObservedProbabilityType,
)
from app.domain.journey.maturity.probability import (
    ObservedProbabilityCalculator,
    calculate_wilson_score_interval,
)
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
    JourneyType,
)


def _make_historical_journey(
    stage_history: list[JourneyStageCode],
    current_stage: JourneyStageCode,
    status: JourneyStatus,
    journey_type: JourneyType = JourneyType.SALES,
) -> JourneyState:
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id="ws-prob-test",
        entity_type="CUSTOMER",
        entity_id=f"cust-{uuid.uuid4().hex[:6]}",
        journey_definition_id=uuid.uuid4(),
        journey_definition_version="1.0.0",
        current_stage=current_stage,
        status=status,
        stage_history=stage_history,
        metadata={"journey_type": journey_type.value},
    )


# ── 1. Wilson Score Interval Math Tests ─────────────────────────────────────────


def test_wilson_score_interval_standard():
    point, low, high = calculate_wilson_score_interval(successes=40, sample_size=100, confidence_level=0.95)
    assert point == 0.40
    assert 0.28 <= low <= 0.35
    assert 0.48 <= high <= 0.55
    assert low < point < high


def test_wilson_score_interval_all_successes():
    point, low, high = calculate_wilson_score_interval(successes=50, sample_size=50, confidence_level=0.95)
    assert point == 1.0
    assert high == pytest.approx(1.0, rel=1e-5)
    assert 0.90 <= low <= 1.0


def test_wilson_score_interval_zero_successes():
    point, low, high = calculate_wilson_score_interval(successes=0, sample_size=50, confidence_level=0.95)
    assert point == 0.0
    assert low == 0.0
    assert 0.0 <= high <= 0.10


def test_wilson_score_interval_zero_total():
    point, low, high = calculate_wilson_score_interval(successes=0, sample_size=0)
    assert point == 0.0
    assert low == 0.0
    assert high == 0.0


# ── 2. Observed Probability Calculator Tests ────────────────────────────────────


def test_probability_insufficient_data_returns_none():
    """
    In accordance with HunterOS architectural principles:
    'No small sample fiction' — if sample size < 30, probability value MUST be None.
    """
    calc = ObservedProbabilityCalculator(default_min_sample=30)

    # Generate only 10 completed historical journeys
    historical: list[JourneyState] = []
    for _ in range(7):
        historical.append(
            _make_historical_journey(
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, JourneyStageCode.CLOSED_WON],
                current_stage=JourneyStageCode.CLOSED_WON,
                status=JourneyStatus.COMPLETED,
            )
        )
    for _ in range(3):
        historical.append(
            _make_historical_journey(
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, JourneyStageCode.CLOSED_LOST],
                current_stage=JourneyStageCode.CLOSED_LOST,
                status=JourneyStatus.LOST,
            )
        )

    prob = calc.calculate_from_historical_cohort(
        workspace_id="ws-prob-test",
        journey_type=JourneyType.SALES,
        current_stage=JourneyStageCode.QUALIFIED,
        historical_journeys=historical,
        target_outcome="CLOSED_WON",
    )

    assert prob.status == ObservedProbabilityStatus.INSUFFICIENT_DATA
    assert prob.value is None
    assert prob.confidence_interval_lower is None
    assert prob.confidence_interval_upper is None
    assert prob.sample_size == 10
    assert prob.minimum_sample_met is False
    assert prob.probability_type == ObservedProbabilityType.HISTORICAL_OBSERVED


def test_probability_sufficient_data_returns_rate_and_wilson_interval():
    calc = ObservedProbabilityCalculator(default_min_sample=30)

    # Generate 50 completed historical journeys (30 won, 20 lost)
    historical: list[JourneyState] = []
    for _ in range(30):
        historical.append(
            _make_historical_journey(
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, JourneyStageCode.PROPOSAL, JourneyStageCode.CLOSED_WON],
                current_stage=JourneyStageCode.CLOSED_WON,
                status=JourneyStatus.COMPLETED,
            )
        )
    for _ in range(20):
        historical.append(
            _make_historical_journey(
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED, JourneyStageCode.CLOSED_LOST],
                current_stage=JourneyStageCode.CLOSED_LOST,
                status=JourneyStatus.LOST,
            )
        )

    prob = calc.calculate_from_historical_cohort(
        workspace_id="ws-prob-test",
        journey_type=JourneyType.SALES,
        current_stage=JourneyStageCode.QUALIFIED,
        historical_journeys=historical,
        target_outcome="CLOSED_WON",
    )

    assert prob.status == ObservedProbabilityStatus.CALCULATED
    assert prob.value is not None
    assert 0.58 <= prob.value <= 0.62  # 30/50 = 0.60
    assert prob.sample_size == 50
    assert prob.minimum_sample_met is True
    assert prob.confidence_interval_lower is not None
    assert prob.confidence_interval_upper is not None
    assert prob.confidence_interval_lower < prob.value < prob.confidence_interval_upper
    assert prob.probability_type == ObservedProbabilityType.HISTORICAL_OBSERVED


def test_probability_no_historical_data():
    calc = ObservedProbabilityCalculator(default_min_sample=30)
    prob = calc.calculate_from_historical_cohort(
        workspace_id="ws-prob-test",
        journey_type=JourneyType.SALES,
        current_stage=JourneyStageCode.QUALIFIED,
        historical_journeys=[],
    )
    assert prob.status == ObservedProbabilityStatus.INSUFFICIENT_DATA
    assert prob.value is None
    assert prob.sample_size == 0
    assert prob.minimum_sample_met is False
