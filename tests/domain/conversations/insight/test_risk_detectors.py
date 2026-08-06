"""
HunterOS Engage V1 - Tests for Risk Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.risks.registry import RiskDetectorRegistry
from app.domain.conversations.insight.detectors.risks.standard import (
    BudgetGapRiskDetector,
    CommunicationGapRiskDetector,
    CustomRiskDetector,
    DelayedResponseRiskDetector,
    MissingDocumentRiskDetector,
    MissingInformationRiskDetector,
    RequirementAmbiguityRiskDetector,
    TimelineConflictRiskDetector,
    UnansweredQuestionRiskDetector,
    register_standard_risk_detectors,
)
from app.domain.conversations.insight.models import InsightCategory, InsightPriority
from app.domain.conversations.timeline.models import TimelineEventCategory, TimelineEventType
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_extracted_fact,
    create_mock_timeline,
    create_mock_timeline_event,
)


def test_missing_information_risk_detector():
    detector = MissingInformationRiskDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="property_type",
            value="3BHK apartment",
            confidence=0.9,
            source_message_ids=["msg-1"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    risks = detector.detect(ctx)

    assert len(risks) >= 1
    assert any(r.category == InsightCategory.MISSING_INFORMATION for r in risks)


def test_unanswered_question_risk_detector():
    detector = UnansweredQuestionRiskDetector()
    event = create_mock_timeline_event(
        event_type=TimelineEventType.QUESTION_ASKED,
        category=TimelineEventCategory.COMMUNICATION,
        title="Question: What is the possession date?",
        description="Buyer asked for possession timeframe",
        source_message_ids=["msg-1"],
    )
    ctx = ConversationInsightContext(timeline=create_mock_timeline(events=[event]))
    risks = detector.detect(ctx)

    assert len(risks) == 1
    assert risks[0].category == InsightCategory.UNANSWERED_QUESTION
    assert "msg-1" in risks[0].evidence.source_message_ids


def test_budget_gap_risk_detector():
    detector = BudgetGapRiskDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.BUDGET_REFERENCE,
            key="budget_concern",
            value="Budget is tight, prices seem too high",
            confidence=0.9,
            source_message_ids=["msg-2"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    risks = detector.detect(ctx)

    assert len(risks) == 1
    assert risks[0].category == InsightCategory.BUDGET_GAP
    assert risks[0].priority == InsightPriority.HIGH


def test_timeline_conflict_risk_detector():
    detector = TimelineConflictRiskDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.DATE_REFERENCE,
            key="possession_date",
            value="Possession delay reported by buyer",
            confidence=0.85,
            source_message_ids=["msg-3"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    risks = detector.detect(ctx)

    assert len(risks) == 1
    assert risks[0].category == InsightCategory.TIMELINE_CONFLICT


def test_requirement_ambiguity_risk_detector():
    detector = RequirementAmbiguityRiskDetector()
    facts = [
        create_mock_extracted_fact(
            category=FactCategory.PROPERTY_REFERENCE,
            key="unit_config",
            value="Not sure if 2BHK or 3BHK, maybe something else",
            confidence=0.88,
            source_message_ids=["msg-4"],
        )
    ]
    ctx = ConversationInsightContext(analysis_result=create_mock_analysis_result(facts=facts))
    risks = detector.detect(ctx)

    assert len(risks) >= 1
    assert any(r.category == InsightCategory.REQUIREMENT_AMBIGUITY for r in risks)


def test_custom_risk_detector_and_registry():
    registry = RiskDetectorRegistry()
    register_standard_risk_detectors(registry)

    assert len(registry.list_detectors()) == 8

    custom = CustomRiskDetector(
        name="SecurityRiskDetector",
        category=InsightCategory.CUSTOM_RISK,
        eval_fn=lambda ctx: [],
    )
    registry.register(custom)
    assert "SecurityRiskDetector" in registry.list_detectors()
    assert registry.get("SecurityRiskDetector") is custom

    registry.unregister("SecurityRiskDetector")
    assert "SecurityRiskDetector" not in registry.list_detectors()
