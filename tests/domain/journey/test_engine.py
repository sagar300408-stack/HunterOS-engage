from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyType,
)
from app.domain.journey.registry import (
    register_core_definitions,
    register_real_estate_definitions,
)
from app.domain.journey.repository import InMemoryJourneyRepository


@pytest.fixture
def engine():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    register_real_estate_definitions()
    return JourneyIntelligenceEngine(
        read_repository=repo,
        write_repository=repo,
    )


def test_create_journey_returns_initialized_state_at_NEW_LEAD(engine):
    state = engine.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_type=JourneyType.SALES,
    )
    assert state.current_stage == JourneyStageCode.NEW_LEAD
    assert state.journey_instance_id is not None


def test_progress_NEW_LEAD_to_INTERESTED_with_inquiry_intent(engine):
    state = engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)
    context = JourneyProgressionContext(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.85}]},
        conversation_context={},
        memory_context={},
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_module="test",
                timestamp=datetime.now(timezone.utc),
                description="Inquiry intent",
                confidence=0.9,
            )
        ],
        evaluated_at=datetime.now(timezone.utc),
    )
    result = engine.progress(context)
    assert result.transition_occurred is True
    assert result.new_stage == JourneyStageCode.INTERESTED


def test_progress_INTERESTED_to_QUALIFIED_with_budget_intent(engine):
    state = engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)
    # First transition
    context = JourneyProgressionContext(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.85}]},
        conversation_context={},
        memory_context={},
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_module="test",
                timestamp=datetime.now(timezone.utc),
                description="Inquiry intent",
                confidence=0.9,
            )
        ],
        evaluated_at=datetime.now(timezone.utc),
    )
    result = engine.progress(context)

    # Second transition
    context2 = JourneyProgressionContext(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=result.new_state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={"detected_intents": [{"intent_type": "BUDGET_CONFIRMED", "confidence": 0.9}]},
        conversation_context={},
        memory_context={},
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_module="test",
                timestamp=datetime.now(timezone.utc),
                description="Budget intent",
                confidence=0.95,
            )
        ],
        evaluated_at=datetime.now(timezone.utc),
    )
    result2 = engine.progress(context2)
    assert result2.transition_occurred is True
    assert result2.new_stage == JourneyStageCode.QUALIFIED


def test_journey_creation_with_real_estate_definition(engine):
    state = engine.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead2",
        journey_type=JourneyType.PROPERTY_PURCHASE,
    )
    assert state.current_stage == JourneyStageCode.NEW_LEAD


def test_get_journey_returns_created_journey(engine):
    state = engine.create_journey("ws1", "CUSTOMER", "lead3", JourneyType.SALES)
    retrieved = engine.get_journey(state.journey_instance_id)
    assert retrieved is not None
    assert retrieved.journey_instance_id == state.journey_instance_id


def test_get_stage_history_returns_correct_history(engine):
    state = engine.create_journey("ws1", "CUSTOMER", "lead4", JourneyType.SALES)
    history = engine.get_stage_history(state.journey_instance_id)
    assert isinstance(history, list)


def test_list_definitions_returns_registered_definitions(engine):
    defs = engine.list_definitions()
    assert len(defs) > 0
