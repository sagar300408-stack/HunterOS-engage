"""
HunterOS Engage V1 - Tests for Conversation Insight Engine (End-to-End)
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.engine import ConversationInsightEngine
from app.domain.conversations.insight.models import (
    ActionOwnerType,
    InsightCategory,
    InsightPriority,
)
from app.domain.conversations.timeline.models import (
    ImportantMomentType,
    TimelineEventCategory,
    TimelineEventType,
)
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_extracted_fact,
    create_mock_important_moment,
    create_mock_timeline,
    create_mock_timeline_event,
)


def _build_rich_test_artifacts():
    ws_id = uuid.uuid4()
    conv_id = "conv-e2e-100"

    facts = [
        create_mock_extracted_fact(
            category=FactCategory.CONTACT_INFO,
            key="phone",
            value="+919876543210",
            confidence=0.98,
            source_message_ids=["msg-1"],
        ),
        create_mock_extracted_fact(
            category=FactCategory.BUDGET_REFERENCE,
            key="budget",
            value="Flexible up to 3.5 Cr",
            confidence=0.94,
            source_message_ids=["msg-2"],
        ),
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="configuration",
            value="Looking for luxury penthouse with private terrace and sea view",
            confidence=0.96,
            source_message_ids=["msg-3"],
        ),
        create_mock_extracted_fact(
            category=FactCategory.DOCUMENT_MENTIONED,
            key="brochure",
            value="Master Layout Plan Brochure",
            confidence=0.92,
            source_message_ids=["msg-4"],
        ),
    ]

    analysis = create_mock_analysis_result(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust-100",
        facts=facts,
        primary_topics=["Luxury Penthouse", "Pricing"],
    )

    ev1 = create_mock_timeline_event(
        event_type=TimelineEventType.QUESTION_ASKED,
        category=TimelineEventCategory.COMMUNICATION,
        title="Question: What are the payment milestones?",
        description="Buyer asked for stage payment structure",
        source_message_ids=["msg-5"],
    )
    ev2 = create_mock_timeline_event(
        event_type=TimelineEventType.FOLLOW_UP_REQUESTED,
        category=TimelineEventCategory.SCHEDULING,
        title="Follow-Up Callback",
        description="Call buyer on Friday morning with updated quote",
        source_message_ids=["msg-6"],
    )
    ev3 = create_mock_timeline_event(
        event_type=TimelineEventType.MEETING_SCHEDULED,
        category=TimelineEventCategory.SCHEDULING,
        title="Site Visit Scheduled",
        description="Joint site walkthrough on Saturday at 11 AM",
        source_message_ids=["msg-7"],
    )

    mom1 = create_mock_important_moment(
        moment_type=ImportantMomentType.FIRST_COMMITMENT,
        title="First Commitment",
        significance="Customer committed to site visit",
        source_message_id="msg-7",
        source_event_id=ev3.event_id,
    )

    timeline = create_mock_timeline(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust-100",
        events=[ev1, ev2, ev3],
        moments=[mom1],
    )

    return analysis, timeline


def test_engine_full_pipeline_execution():
    engine = ConversationInsightEngine()
    analysis, timeline = _build_rich_test_artifacts()

    result = engine.build_insights(analysis_result=analysis, timeline=timeline)

    assert result is not None
    assert result.conversation_id == "conv-e2e-100"
    assert result.customer_id == "cust-100"

    # Verify diagnostics & 8-stage execution
    assert len(result.diagnostics.stages_executed) == 8
    assert result.diagnostics.is_valid is True

    # Verify insights detected
    assert len(result.risks) > 0
    assert len(result.opportunities) > 0
    assert len(result.action_items) > 0
    assert len(result.all_insights) == len(result.risks) + len(result.opportunities) + len(result.action_items)

    # Verify metadata
    assert result.metadata.total_insights == len(result.all_insights)
    assert result.metadata.total_risks == len(result.risks)
    assert result.metadata.total_opportunities == len(result.opportunities)
    assert result.metadata.total_action_items == len(result.action_items)

    # Verify view renderings
    exec_view = engine.render_view(result, "executive")
    assert exec_view["view"] == "executive"
    assert exec_view["conversation_id"] == "conv-e2e-100"

    sales_view = engine.render_view(result, "sales")
    assert sales_view["view"] == "sales"

    ops_view = engine.render_view(result, "operations")
    assert ops_view["view"] == "operations"

    audit_view = engine.render_view(result, "audit")
    assert audit_view["view"] == "audit"
    assert audit_view["total_insights"] == len(result.all_insights)


def test_engine_persists_in_repository():
    engine = ConversationInsightEngine()
    analysis, timeline = _build_rich_test_artifacts()

    result = engine.build_insights(analysis_result=analysis, timeline=timeline)

    saved = engine.repository.get_by_id(result.insight_result_id)
    assert saved is not None
    assert saved.conversation_id == result.conversation_id
