"""
HunterOS Engage V1 - Tests for Insight REST API Router
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.engine import default_conversation_insight_engine
from app.domain.conversations.insight.repository import default_insight_repository
from app.domain.conversations.timeline.models import (
    TimelineEventCategory,
    TimelineEventType,
)
from app.main import create_app
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_extracted_fact,
    create_mock_timeline,
    create_mock_timeline_event,
)

app = create_app()
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    conv_id = "conv-api-test-001"
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.CONTACT_INFO,
            key="phone",
            value="+919876543210",
            confidence=0.95,
            source_message_ids=["msg-1"],
        ),
        create_mock_extracted_fact(
            category=FactCategory.BUDGET_REFERENCE,
            key="budget",
            value="3.5 Cr",
            confidence=0.95,
            source_message_ids=["msg-2"],
        ),
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="req",
            value="Penthouse with private terrace",
            confidence=0.95,
            source_message_ids=["msg-3"],
        ),
    ]

    analysis = create_mock_analysis_result(
        conversation_id=conv_id,
        customer_id="cust-001",
        facts=facts,
    )

    event = create_mock_timeline_event(
        event_type=TimelineEventType.FOLLOW_UP_REQUESTED,
        category=TimelineEventCategory.SCHEDULING,
        title="Follow Up",
        description="Call back on Monday",
        source_message_ids=["msg-4"],
    )

    timeline = create_mock_timeline(
        conversation_id=conv_id,
        customer_id="cust-001",
        events=[event],
    )

    # Generate insights and store in default repo
    default_conversation_insight_engine.build_insights(analysis_result=analysis, timeline=timeline)


def test_get_conversation_insights_endpoint():
    response = client.get("/api/v1/conversations/conv-api-test-001/insights")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "conv-api-test-001"
    assert "risks" in data
    assert "opportunities" in data
    assert "action_items" in data


def test_get_conversation_risks_endpoint():
    response = client.get("/api/v1/conversations/conv-api-test-001/insights/risks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_conversation_opportunities_endpoint():
    response = client.get("/api/v1/conversations/conv-api-test-001/insights/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_conversation_action_items_endpoint():
    response = client.get("/api/v1/conversations/conv-api-test-001/insights/action-items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_render_view_endpoint():
    response = client.get("/api/v1/conversations/conv-api-test-001/insights/views/executive")
    assert response.status_code == 200
    data = response.json()
    assert data["view"] == "executive"
    assert data["conversation_id"] == "conv-api-test-001"


def test_404_not_found():
    response = client.get("/api/v1/conversations/non-existent-conv/insights")
    assert response.status_code == 404
