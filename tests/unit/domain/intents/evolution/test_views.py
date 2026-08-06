"""
Unit tests for Executive, Sales, Operations, and Audit Perspective Evolution Views.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.evolution.api import IntentEvolutionAPIv1
from app.domain.intents.evolution.models import (
    EntityType,
    EvolutionDiagnostics,
    EvolutionMetadata,
    IntentEvolutionResult,
    IntentHistory,
    IntentLifecycleState,
    IntentTimeline,
    IntentVelocity,
)
from app.domain.intents.evolution.views.audit import AuditEvolutionView
from app.domain.intents.evolution.views.executive import ExecutiveEvolutionView
from app.domain.intents.evolution.views.operations import OperationsEvolutionView
from app.domain.intents.evolution.views.sales import SalesEvolutionView


@pytest.fixture
def sample_evolution_result():
    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    timeline = IntentTimeline(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-views-1",
        intent_name="PricingInquiry",
        taxonomy_path="Sales/Pricing/Enterprise",
        first_detected_at=now,
        last_observed_at=now,
        observation_frequency=3,
        velocity=IntentVelocity.INCREASING,
        source_conversations=["c1", "c2", "c3"],
        current_lifecycle_state=IntentLifecycleState.STRENGTHENING,
        current_confidence=0.96,
    )

    history = IntentHistory(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-views-1",
        canonical_intent_name="PricingInquiry",
        current_state=IntentLifecycleState.STRENGTHENING,
        timeline=timeline,
        created_at=now,
        updated_at=now,
    )

    return IntentEvolutionResult(
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-views-1",
        current_conversation_id="c3",
        intent_histories=[history],
        timelines=[timeline],
        metadata=EvolutionMetadata(
            entity_type=EntityType.CUSTOMER,
            entity_id="cust-views-1",
            total_active_intents=0,
            total_strengthening_intents=1,
        ),
        diagnostics=EvolutionDiagnostics(is_valid=True),
        generated_at=now,
    )


def test_executive_view(sample_evolution_result):
    view = ExecutiveEvolutionView()
    proj = view.project(sample_evolution_result)

    assert proj["view"] == "executive"
    assert proj["entity_id"] == "cust-views-1"
    assert proj["summary"]["total_strengthening_intents"] == 1
    assert proj["velocity_distribution"]["INCREASING"] == 1
    assert len(proj["top_intents"]) == 1


def test_sales_view(sample_evolution_result):
    view = SalesEvolutionView()
    proj = view.project(sample_evolution_result)

    assert proj["view"] == "sales"
    assert len(proj["strengthening_commercial_signals"]) == 1
    assert len(proj["tracked_commercial_intents"]) == 1
    assert proj["total_commercial_signals"] == 1


def test_operations_view(sample_evolution_result):
    view = OperationsEvolutionView()
    proj = view.project(sample_evolution_result)

    assert proj["view"] == "operations"
    assert "fulfillment_and_service_intents" in proj


def test_audit_view(sample_evolution_result):
    view = AuditEvolutionView()
    proj = view.project(sample_evolution_result)

    assert proj["view"] == "audit"
    assert "event_stream" in proj
    assert "diagnostics" in proj


def test_api_view_dispatch(sample_evolution_result):
    api = IntentEvolutionAPIv1()
    proj = api.get_evolution_view(sample_evolution_result, "executive")
    assert proj["view"] == "executive"

    with pytest.raises(ValueError, match="Unknown evolution perspective"):
        api.get_evolution_view(sample_evolution_result, "invalid_view")
