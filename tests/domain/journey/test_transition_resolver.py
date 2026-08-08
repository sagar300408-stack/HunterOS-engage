from __future__ import annotations
import uuid
import pytest
from app.domain.journey.models import (
    TransitionCandidate,
    JourneyStageCode,
    TransitionType,
    ConfidenceFactors
)
from app.domain.journey.progression.engine import StageTransitionResolver
from app.domain.journey.definitions.core import build_sales_journey_definition

@pytest.fixture
def sales_definition():
    return build_sales_journey_definition()

@pytest.fixture
def resolver():
    return StageTransitionResolver()

def build_candidate(to_stage: JourneyStageCode, confidence: float, transition_type: TransitionType = TransitionType.ADVANCE, evidence_count: int = 1) -> TransitionCandidate:
    return TransitionCandidate(
        from_stage=JourneyStageCode.NEW_LEAD,
        to_stage=to_stage,
        transition_type=transition_type,
        evidence=[None] * evidence_count,  # Dummy evidence
        confidence=confidence,
        confidence_factors=ConfidenceFactors(),
        rule_name="TestRule",
        reason="Test",
        source_modules=["test"]
    )

def test_resolver_selects_highest_confidence(resolver, sales_definition):
    candidates = [
        build_candidate(JourneyStageCode.INTERESTED, 0.6),
        build_candidate(JourneyStageCode.QUALIFIED, 0.9)
    ]
    # NEW_LEAD -> QUALIFIED might not be in definition, wait, NEW_LEAD -> QUALIFIED might be invalid in standard definition.
    # Let's use valid ones from INTERESTED
    c1 = TransitionCandidate(
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.QUALIFIED,
        transition_type=TransitionType.ADVANCE,
        evidence=[None], confidence=0.7, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    c2 = TransitionCandidate(
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.CLOSED_LOST,
        transition_type=TransitionType.CLOSURE,
        evidence=[None], confidence=0.9, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    accepted, rejected = resolver.resolve([c1, c2], sales_definition, JourneyStageCode.INTERESTED)
    assert accepted == c2
    assert c1 in rejected
    assert len(rejected) == 1

def test_resolver_rejects_invalid_transitions(resolver, sales_definition):
    # Try a completely invalid transition in sales_definition (e.g. INTERESTED -> BOOKING)
    c1 = TransitionCandidate(
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.BOOKING,
        transition_type=TransitionType.ADVANCE,
        evidence=[None], confidence=0.9, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    accepted, rejected = resolver.resolve([c1], sales_definition, JourneyStageCode.INTERESTED)
    assert accepted is None
    assert c1 in rejected

def test_resolver_preserves_rejected_candidates(resolver, sales_definition):
    c1 = TransitionCandidate(
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.QUALIFIED,
        transition_type=TransitionType.ADVANCE,
        evidence=[None], confidence=0.8, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    c2 = TransitionCandidate(
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.CLOSED_LOST,
        transition_type=TransitionType.CLOSURE,
        evidence=[None], confidence=0.7, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    accepted, rejected = resolver.resolve([c1, c2], sales_definition, JourneyStageCode.INTERESTED)
    assert accepted == c1
    assert c2 in rejected

def test_resolver_returns_none_for_empty(resolver, sales_definition):
    accepted, rejected = resolver.resolve([], sales_definition, JourneyStageCode.INTERESTED)
    assert accepted is None
    assert rejected == []

def test_resolver_allows_reactivation_from_terminal(resolver, sales_definition):
    c1 = TransitionCandidate(
        from_stage=JourneyStageCode.CLOSED_LOST,
        to_stage=JourneyStageCode.INTERESTED,
        transition_type=TransitionType.REACTIVATION,
        evidence=[None], confidence=0.8, confidence_factors=ConfidenceFactors(), rule_name="", reason="", source_modules=[]
    )
    accepted, rejected = resolver.resolve([c1], sales_definition, JourneyStageCode.CLOSED_LOST)
    assert accepted == c1
    assert not rejected
