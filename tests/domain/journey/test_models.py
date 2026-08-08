from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

import pytest

from app.domain.journey.models import (
    ConfidenceFactors,
    EvidenceType,
    JourneyDefinition,
    JourneyDiagnostics,
    JourneyEvidence,
    JourneyMetadata,
    JourneyProgressionResult,
    JourneyProvenance,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
    JourneyTimelineEvent,
    JourneyType,
    StageDefinition,
    TimelineEventType,
    TransitionCandidate,
    TransitionType,
)


def test_enums_have_expected_values() -> None:
    assert JourneyType.SALES.value == "SALES"
    assert JourneyType.PROPERTY_PURCHASE.value == "PROPERTY_PURCHASE"
    assert JourneyStatus.ACTIVE.value == "ACTIVE"
    assert JourneyStatus.COMPLETED.value == "COMPLETED"
    assert JourneyStatus.LOST.value == "LOST"
    assert TransitionType.ADVANCE.value == "ADVANCE"
    assert TransitionType.REGRESSION.value == "REGRESSION"
    assert TransitionType.REACTIVATION.value == "REACTIVATION"
    assert EvidenceType.INTENT.value == "INTENT"
    assert EvidenceType.CONVERSATION.value == "CONVERSATION"
    assert TimelineEventType.STAGE_ENTERED.value == "STAGE_ENTERED"
    assert TimelineEventType.JOURNEY_STARTED.value == "JOURNEY_STARTED"


def test_journey_evidence_frozen() -> None:
    evidence = JourneyEvidence(
        evidence_id=uuid.uuid4(),
        evidence_type=EvidenceType.INTENT,
        source_module="intent_engine",
        timestamp=datetime.now(timezone.utc),
        description="intent buy",
        confidence=0.9,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.confidence = 0.5  # type: ignore


def test_confidence_factors_compute_aggregate() -> None:
    cf = ConfidenceFactors(
        intent_match=0.8,
        timeline_match=0.9,
        conversation_match=0.7,
        rule_strength=1.0,
    )
    agg = cf.compute_aggregate()
    assert 0.0 <= agg <= 1.0
    assert agg > 0.7

    cf_zero = ConfidenceFactors()
    assert cf_zero.compute_aggregate() == 0.0


def test_journey_state_compute_progression_fingerprint(sample_journey_state: JourneyState) -> None:
    evidence_ids = ["ev-1", "ev-2"]
    fp1 = sample_journey_state.compute_progression_fingerprint(evidence_ids, "1.0.0")
    fp2 = sample_journey_state.compute_progression_fingerprint(evidence_ids, "1.0.0")
    assert fp1 == fp2

    # Change state and check fingerprint changes
    sample_journey_state.current_stage = JourneyStageCode.QUALIFIED
    fp3 = sample_journey_state.compute_progression_fingerprint(evidence_ids, "1.0.0")
    assert fp1 != fp3


def test_journey_state_mutable(sample_journey_state: JourneyState) -> None:
    assert sample_journey_state.current_stage == JourneyStageCode.NEW_LEAD
    sample_journey_state.current_stage = JourneyStageCode.QUALIFIED
    assert sample_journey_state.current_stage == JourneyStageCode.QUALIFIED


def test_frozen_dataclasses() -> None:
    frozen_classes = [
        ConfidenceFactors,
        JourneyProvenance,
        JourneyMetadata,
        JourneyDiagnostics,
        StageDefinition,
        JourneyDefinition,
        JourneyStageTransition,
        JourneyTimelineEvent,
        TransitionCandidate,
        JourneyProgressionResult,
    ]

    for cls in frozen_classes:
        assert getattr(cls, "__dataclass_params__").frozen is True


def test_transition_candidate_creation() -> None:
    candidate = TransitionCandidate(
        from_stage=JourneyStageCode.NEW_LEAD,
        to_stage=JourneyStageCode.QUALIFIED,
        transition_type=TransitionType.ADVANCE,
        confidence=0.9,
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_module="test",
                timestamp=datetime.now(timezone.utc),
                description="Test evidence",
                confidence=0.9,
            )
        ],
        confidence_factors=ConfidenceFactors(intent_match=0.9),
        rule_name="TestRule",
        reason="Strong intent detected",
    )
    assert candidate.to_stage == JourneyStageCode.QUALIFIED
    assert candidate.confidence == 0.9
    assert len(candidate.evidence) == 1
