from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone
from app.domain.journey.models import (
    JourneyState,
    JourneyStageCode,
    JourneyStatus,
    JourneyType,
    EvidenceType
)
from app.domain.journey.exceptions import JourneyNotFoundError, JourneyDefinitionError
from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.progression.engine import StageProgressionEngine

@pytest.fixture
def sales_definition():
    return build_sales_journey_definition()

@pytest.fixture
def engine():
    return StageProgressionEngine()

def build_state(stage: JourneyStageCode, entity_id: str, workspace_id: uuid.UUID) -> JourneyState:
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        status=JourneyStatus.ACTIVE,
        current_stage=stage,
        stage_history=[]
    )

def test_pipeline_new_lead_to_interested(engine, sales_definition):
    workspace_id = uuid.uuid4()
    entity_id = str(uuid.uuid4())
    context = JourneyProgressionContext(
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        journey_state=build_state(JourneyStageCode.NEW_LEAD, entity_id, workspace_id),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.9}]},
        evidence=[]
    )
    result = engine.progress(context)
    assert result.did_progress is True
    assert result.new_stage == JourneyStageCode.INTERESTED
    assert result.transition is not None

def test_pipeline_no_change_when_no_evidence(engine, sales_definition):
    workspace_id = uuid.uuid4()
    entity_id = str(uuid.uuid4())
    context = JourneyProgressionContext(
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        journey_state=build_state(JourneyStageCode.NEW_LEAD, entity_id, workspace_id),
        journey_definition=sales_definition,
        evidence=[]
    )
    result = engine.progress(context)
    assert result.did_progress is False
    assert result.new_stage is None

def test_pipeline_diagnostics_contain_correct_counts(engine, sales_definition):
    workspace_id = uuid.uuid4()
    entity_id = str(uuid.uuid4())
    context = JourneyProgressionContext(
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        journey_state=build_state(JourneyStageCode.NEW_LEAD, entity_id, workspace_id),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.9}]},
        evidence=[]
    )
    result = engine.progress(context)
    assert result.diagnostics is not None
    assert result.diagnostics.accepted_transition_count == 1
    assert result.diagnostics.rules_evaluated > 0

def test_pipeline_provenance_is_populated(engine, sales_definition):
    workspace_id = uuid.uuid4()
    entity_id = str(uuid.uuid4())
    context = JourneyProgressionContext(
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        journey_state=build_state(JourneyStageCode.NEW_LEAD, entity_id, workspace_id),
        journey_definition=sales_definition,
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.9}]},
        evidence=[]
    )
    result = engine.progress(context)
    assert result.provenance is not None
    assert result.provenance.definition_version == sales_definition.version
    assert "journey.progression" in result.provenance.source_modules

def test_pipeline_handles_missing_journey_state(engine, sales_definition):
    context = JourneyProgressionContext(
        workspace_id=uuid.uuid4(),
        entity_type="lead",
        entity_id=str(uuid.uuid4()),
        journey_state=None,
        journey_definition=sales_definition,
        evidence=[]
    )
    with pytest.raises(JourneyNotFoundError):
        engine.progress(context)

def test_pipeline_handles_missing_definition(engine):
    workspace_id = uuid.uuid4()
    entity_id = str(uuid.uuid4())
    context = JourneyProgressionContext(
        workspace_id=workspace_id,
        entity_type="lead",
        entity_id=entity_id,
        journey_state=build_state(JourneyStageCode.NEW_LEAD, entity_id, workspace_id),
        journey_definition=None,
        evidence=[]
    )
    with pytest.raises(JourneyDefinitionError):
        engine.progress(context)
