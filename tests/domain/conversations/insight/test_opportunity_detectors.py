"""
HunterOS Engage V1 - Tests for Opportunity Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.opportunities.registry import (
    OpportunityDetectorRegistry,
)
from app.domain.conversations.insight.detectors.opportunities.standard import (
    AdditionalRequirementOpportunityDetector,
    CrossSellOpportunityDetector,
    CustomOpportunityDetector,
    DocumentSharingOpportunityDetector,
    FollowUpOpportunityDetector,
    MeetingOpportunityDetector,
    QualificationOpportunityDetector,
    UpsellOpportunityDetector,
    register_standard_opportunity_detectors,
)
from app.domain.conversations.insight.models import InsightCategory, InsightPriority
from app.domain.conversations.timeline.models import ImportantMomentType
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_extracted_fact,
    create_mock_important_moment,
    create_mock_timeline,
)


def test_upsell_opportunity_detector():
    detector = UpsellOpportunityDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="config",
            value="Looking for luxury penthouse with sea view",
            confidence=0.95,
            source_message_ids=["msg-10"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    opps = detector.detect(ctx)

    assert len(opps) >= 1
    assert opps[0].category == InsightCategory.UPSELL
    assert opps[0].priority == InsightPriority.HIGH


def test_cross_sell_opportunity_detector():
    detector = CrossSellOpportunityDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="interior",
            value="Also need complete interior design assistance",
            confidence=0.90,
            source_message_ids=["msg-11"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    opps = detector.detect(ctx)

    assert len(opps) == 1
    assert opps[0].category == InsightCategory.CROSS_SELL


def test_follow_up_opportunity_detector():
    detector = FollowUpOpportunityDetector()
    moment = create_mock_important_moment(
        moment_type=ImportantMomentType.FIRST_COMMITMENT,
        title="First Agreement",
        significance="Buyer agreed to evaluate project proposal",
        source_message_id="msg-20",
    )
    ctx = ConversationInsightContext(timeline=create_mock_timeline(moments=[moment]))
    opps = detector.detect(ctx)

    assert len(opps) == 1
    assert opps[0].category == InsightCategory.FOLLOW_UP


def test_qualification_opportunity_detector():
    detector = QualificationOpportunityDetector()
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
            value="3BHK East facing",
            confidence=0.95,
            source_message_ids=["msg-3"],
        ),
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    opps = detector.detect(ctx)

    assert len(opps) == 1
    assert opps[0].category == InsightCategory.QUALIFICATION
    assert "Budget specified" in opps[0].qualification_criteria


def test_opportunity_registry():
    registry = OpportunityDetectorRegistry()
    register_standard_opportunity_detectors(registry)

    assert len(registry.list_detectors()) == 7
    assert registry.get("UpsellOpportunityDetector") is not None
