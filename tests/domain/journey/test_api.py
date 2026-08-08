from __future__ import annotations

import uuid
import pytest
from app.domain.journey.api import JourneyIntelligenceAPIv1
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.models import JourneyStageCode, JourneyType
from app.domain.journey.registry import (
    register_core_definitions,
    register_real_estate_definitions,
)
from app.domain.journey.repository import InMemoryJourneyRepository


@pytest.fixture
def api():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    register_real_estate_definitions()
    engine = JourneyIntelligenceEngine(
        read_repository=repo,
        write_repository=repo,
    )
    return JourneyIntelligenceAPIv1(engine=engine)


def test_api_create_journey_works(api):
    response = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_type=JourneyType.SALES,
    )
    assert response.current_stage == JourneyStageCode.NEW_LEAD
    assert response.journey_instance_id is not None


def test_api_progress_journey_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_type=JourneyType.SALES,
    )
    response = api.progress_journey(
        journey_instance_id=state.journey_instance_id,
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.85}]},
        conversation_context={},
        memory_context={},
    )
    assert response is not None
    assert response.journey_instance_id == state.journey_instance_id


def test_api_get_journey_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead2",
        journey_type=JourneyType.SALES,
    )
    retrieved = api.get_journey(state.journey_instance_id)
    assert retrieved is not None
    assert retrieved.journey_instance_id == state.journey_instance_id


def test_api_get_executive_view_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead3",
        journey_type=JourneyType.SALES,
    )
    view = api.get_executive_view(state.journey_instance_id)
    assert isinstance(view, dict)
    assert "current_stage" in view


def test_api_get_sales_view_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead4",
        journey_type=JourneyType.SALES,
    )
    view = api.get_sales_view(state.journey_instance_id)
    assert isinstance(view, dict)
    assert "current_stage" in view


def test_api_get_operations_view_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead5",
        journey_type=JourneyType.SALES,
    )
    view = api.get_operations_view(state.journey_instance_id)
    assert isinstance(view, dict)
    assert "operational_stage" in view


def test_api_get_audit_view_works(api):
    state = api.create_journey(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead6",
        journey_type=JourneyType.SALES,
    )
    view = api.get_audit_view(state.journey_instance_id)
    assert isinstance(view, dict)
    assert "provenance" in view
