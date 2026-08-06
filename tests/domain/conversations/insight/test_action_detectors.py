"""
HunterOS Engage V1 - Tests for Action Item Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.actions.registry import (
    ActionItemDetectorRegistry,
)
from app.domain.conversations.insight.detectors.actions.standard import (
    CustomActionItemDetector,
    CustomerActionItemDetector,
    InternalTeamActionItemDetector,
    PendingResponseActionItemDetector,
    RequestedDocumentActionItemDetector,
    ScheduledActivityActionItemDetector,
    SharedActionItemDetector,
    register_standard_action_item_detectors,
)
from app.domain.conversations.insight.models import (
    ActionOwnerType,
    InsightCategory,
    InsightPriority,
)
from app.domain.conversations.timeline.models import TimelineEventCategory, TimelineEventType
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_extracted_fact,
    create_mock_timeline,
    create_mock_timeline_event,
)


def test_customer_action_item_detector():
    detector = CustomerActionItemDetector()
    event = create_mock_timeline_event(
        event_type=TimelineEventType.AGREEMENT_REACHED,
        category=TimelineEventCategory.COMMITMENT,
        title="Customer agreed to terms",
        description="Customer confirmed they will send ID documents",
        source_message_ids=["msg-1"],
    )
    ctx = ConversationInsightContext(timeline=create_mock_timeline(events=[event]))
    actions = detector.detect(ctx)

    assert len(actions) == 1
    assert actions[0].owner_type == ActionOwnerType.CUSTOMER
    assert actions[0].category == InsightCategory.CUSTOMER_ACTION


def test_internal_team_action_item_detector():
    detector = InternalTeamActionItemDetector()
    event = create_mock_timeline_event(
        event_type=TimelineEventType.FOLLOW_UP_REQUESTED,
        category=TimelineEventCategory.SCHEDULING,
        title="Follow-Up Callback Scheduled",
        description="Agent promised to call back on Friday morning",
        source_message_ids=["msg-2"],
    )
    ctx = ConversationInsightContext(timeline=create_mock_timeline(events=[event]))
    actions = detector.detect(ctx)

    assert len(actions) == 1
    assert actions[0].owner_type == ActionOwnerType.INTERNAL_TEAM
    assert actions[0].category == InsightCategory.INTERNAL_TEAM_ACTION


def test_shared_action_item_detector():
    detector = SharedActionItemDetector()
    event = create_mock_timeline_event(
        event_type=TimelineEventType.MEETING_SCHEDULED,
        category=TimelineEventCategory.SCHEDULING,
        title="Site Visit Scheduled",
        description="Customer and sales rep scheduled site visit for Sunday 11 AM",
        source_message_ids=["msg-3"],
    )
    ctx = ConversationInsightContext(timeline=create_mock_timeline(events=[event]))
    actions = detector.detect(ctx)

    assert len(actions) == 1
    assert actions[0].owner_type == ActionOwnerType.SHARED
    assert actions[0].priority in (InsightPriority.HIGH, InsightPriority.CRITICAL)


def test_requested_document_action_detector():
    detector = RequestedDocumentActionItemDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.DOCUMENT_MENTIONED,
            key="brochure",
            value="Master Layout Plan Brochure",
            confidence=0.9,
            source_message_ids=["msg-4"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    actions = detector.detect(ctx)

    assert len(actions) == 1
    assert actions[0].category == InsightCategory.REQUESTED_DOCUMENT


def test_action_item_registry():
    registry = ActionItemDetectorRegistry()
    register_standard_action_item_detectors(registry)

    assert len(registry.list_detectors()) == 6
    assert registry.get("InternalTeamActionItemDetector") is not None
