from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone
from app.domain.journey.models import (
    JourneyState,
    JourneyStageCode,
    JourneyStatus,
    JourneyType,
    JourneyEvidence,
    EvidenceType,
    TransitionType
)
from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.progression.rules import (
    EngagementRule,
    QualificationRule,
    NegotiationRule,
    BookingRule,
    CompletionRule,
    CancellationRule,
    InactivityRule,
    ReactivationRule
)

@pytest.fixture
def sales_definition():
    return build_sales_journey_definition()

def build_state(stage: JourneyStageCode) -> JourneyState:
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id="foo",
        status=JourneyStatus.ACTIVE,
        current_stage=stage,
        stage_history=[]
    )

def test_engagement_rule(sales_definition):
    rule = EngagementRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.NEW_LEAD),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.9}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.INTERESTED
    assert candidate.transition_type == TransitionType.ADVANCE
    assert candidate.confidence_factors is not None

def test_qualification_rule(sales_definition):
    rule = QualificationRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.INTERESTED),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "BUDGET_DISCUSSION", "confidence": 0.8}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.QUALIFIED
    assert candidate.confidence_factors is not None

def test_negotiation_rule(sales_definition):
    rule = NegotiationRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.QUALIFIED),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "NEGOTIATION", "confidence": 0.85}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.NEGOTIATION

def test_booking_rule(sales_definition):
    rule = BookingRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.NEGOTIATION),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "BOOKING_INTEREST", "confidence": 0.9}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.BOOKING

def test_completion_rule(sales_definition):
    rule = CompletionRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.BOOKING),
        journey_definition=sales_definition,
        conversation_context={"timeline_events": [{"event_type": "DEAL_CLOSED"}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.CLOSED_WON
    assert candidate.transition_type == TransitionType.COMPLETION

def test_cancellation_rule(sales_definition):
    rule = CancellationRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.INTERESTED),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "CANCELLATION", "confidence": 0.9}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.CLOSED_LOST
    assert candidate.transition_type == TransitionType.CLOSURE

def test_inactivity_rule(sales_definition):
    rule = InactivityRule()
    evidence = [JourneyEvidence(
        evidence_id=uuid.uuid4(),
        evidence_type=EvidenceType.SYSTEM,
        source_module="test",
        timestamp=datetime.now(timezone.utc),
        description="user is inactive",
        confidence=1.0
    )]
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.INTERESTED),
        journey_definition=sales_definition,
        evidence=evidence
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.INACTIVE
    assert candidate.transition_type == TransitionType.CLOSURE

def test_reactivation_rule(sales_definition):
    rule = ReactivationRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.INACTIVE),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "GENERAL_INQUIRY", "confidence": 0.9}]},
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is not None
    assert candidate.to_stage == JourneyStageCode.INTERESTED
    assert candidate.transition_type == TransitionType.REACTIVATION

def test_rules_return_none_no_evidence(sales_definition):
    rule = EngagementRule()
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=uuid.uuid4(),
        journey_state=build_state(JourneyStageCode.NEW_LEAD),
        journey_definition=sales_definition,
        evidence=[]
    )
    candidate = rule.evaluate(context)
    assert candidate is None
