from __future__ import annotations

import pytest
import uuid
from datetime import datetime, timezone
from app.domain.journey.models import *
from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.definitions.industry.real_estate import build_real_estate_sales_journey
from app.domain.journey.repository import InMemoryJourneyRepository
from app.domain.journey.query import JourneyQueryEngine
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.progression.engine import StageProgressionEngine
from app.domain.journey.definitions.registry import JourneyDefinitionRegistry, StageDefinitionRegistry
from app.domain.journey.definitions.core import register_core_definitions
from app.domain.journey.definitions.industry.real_estate import register_real_estate_definitions

@pytest.fixture
def workspace_id():
    return str(uuid.uuid4())

@pytest.fixture
def sales_definition():
    return build_sales_journey_definition()

@pytest.fixture
def real_estate_definition():
    return build_real_estate_sales_journey()

@pytest.fixture
def repository():
    return InMemoryJourneyRepository()

@pytest.fixture
def journey_engine(repository):
    journey_reg = JourneyDefinitionRegistry()
    stage_reg = StageDefinitionRegistry()
    register_core_definitions(journey_reg, stage_reg)
    register_real_estate_definitions(journey_reg, stage_reg)
    return JourneyIntelligenceEngine(
        journey_registry=journey_reg,
        stage_registry=stage_reg,
        progression_engine=StageProgressionEngine(),
        read_repository=repository,
        write_repository=repository,
        query_engine=JourneyQueryEngine(repository),
    )

@pytest.fixture
def sample_journey_state(workspace_id, sales_definition):
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id=workspace_id,
        entity_type='CUSTOMER',
        entity_id='customer-001',
        journey_definition_id=sales_definition.journey_id,
        journey_definition_version=sales_definition.version,
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD],
    )

@pytest.fixture
def intent_context_with_inquiry():
    return {'detected_intents': [{'intent_type': 'PROPERTY_INQUIRY', 'confidence': 0.85}]}

@pytest.fixture
def intent_context_with_negotiation():
    return {'detected_intents': [{'intent_type': 'NEGOTIATION', 'confidence': 0.90}]}

@pytest.fixture 
def intent_context_with_booking():
    return {'detected_intents': [{'intent_type': 'BOOKING_INTEREST', 'confidence': 0.88}]}

@pytest.fixture
def intent_context_with_cancellation():
    return {'detected_intents': [{'intent_type': 'CANCELLATION', 'confidence': 0.92}]}

@pytest.fixture
def conversation_context_with_pricing():
    return {'topics': [{'name': 'Pricing Discussion'}, {'name': 'Discount Request'}]}

@pytest.fixture
def conversation_context_with_site_visit():
    return {'topics': [{'name': 'Site Visit'}], 'timeline_events': [{'event_type': 'SITE_VISIT_SCHEDULED'}]}
