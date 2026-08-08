from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.definitions.core import build_sales_journey_definition
from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
)
from app.domain.journey.views import (
    AuditJourneyView,
    ExecutiveJourneyView,
    OperationsJourneyView,
    SalesJourneyView,
)


@pytest.fixture
def journey_state():
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )


def test_executive_journey_view_render_returns_expected_keys(journey_state):
    definition = build_sales_journey_definition()
    rendered = ExecutiveJourneyView.render(journey_state, definition, [])
    assert "current_stage" in rendered
    assert "journey_status" in rendered
    assert "stage_duration_days" in rendered


def test_sales_journey_view_render_returns_expected_keys(journey_state):
    rendered = SalesJourneyView.render(journey_state, [])
    assert "current_stage" in rendered
    assert "commercial_evidence" in rendered


def test_operations_journey_view_render_returns_expected_keys(journey_state):
    timeline = JourneyTimeline(journey_instance_id=journey_state.journey_instance_id)
    rendered = OperationsJourneyView.render(journey_state, [], timeline)
    assert "operational_stage" in rendered
    assert "scheduled_events" in rendered


def test_audit_journey_view_render_returns_expected_keys(journey_state):
    timeline = JourneyTimeline(journey_instance_id=journey_state.journey_instance_id)
    rendered = AuditJourneyView.render(journey_state, [], [], timeline)
    assert "complete_transition_graph" in rendered
    assert "evidence_audit" in rendered


def test_views_contain_no_recommendation_fields(journey_state):
    definition = build_sales_journey_definition()
    timeline = JourneyTimeline(journey_instance_id=journey_state.journey_instance_id)
    exec_view = ExecutiveJourneyView.render(journey_state, definition, [])
    sales_view = SalesJourneyView.render(journey_state, [])
    ops_view = OperationsJourneyView.render(journey_state, [], timeline)
    audit_view = AuditJourneyView.render(journey_state, [], [], timeline)

    for view in [exec_view, sales_view, ops_view, audit_view]:
        rendered_str = str(view).lower()
        assert "recommendation" not in rendered_str
        assert "predict" not in rendered_str
