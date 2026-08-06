"""
HunterOS Engage V1 - Tests for Insight Classification & Validation Framework
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.insight.classification import InsightClassifier
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    InsightCategory,
    InsightEvidence,
    InsightPriority,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.insight.validation import (
    FORBIDDEN_DOMAIN_KEYS,
    InsightValidationFramework,
)
from tests.domain.conversations.insight.helpers import (
    create_mock_analysis_result,
    create_mock_timeline,
)


def test_insight_classifier_harmonization():
    classifier = InsightClassifier()
    ctx = ConversationInsightContext(conversation_id="conv-1")

    ev = InsightEvidence(source_message_ids=["msg-1"], extraction_method="TEST")
    ctx.raw_risks = [
        RiskInsight(
            category=InsightCategory.BUDGET_GAP,
            title="Budget Risk",
            description="Budget mismatch",
            priority=InsightPriority.HIGH,
            confidence=0.95,
            evidence=ev,
        )
    ]
    ctx.raw_opportunities = [
        OpportunityInsight(
            category=InsightCategory.UPSELL,
            title="Upsell Penthouse",
            description="Upgrade floor plan",
            priority=InsightPriority.MEDIUM,
            confidence=0.88,
            evidence=ev,
        )
    ]
    ctx.raw_action_items = [
        ActionItemInsight(
            category=InsightCategory.INTERNAL_TEAM_ACTION,
            owner_type=ActionOwnerType.INTERNAL_TEAM,
            title="Send Quotation",
            description="Prepare quote",
            priority=InsightPriority.HIGH,
            confidence=0.92,
            evidence=ev,
        )
    ]

    classifier.classify_and_harmonize(ctx)

    assert len(ctx.classified_risks) == 1
    assert len(ctx.classified_opportunities) == 1
    assert len(ctx.classified_action_items) == 1
    assert len(ctx.all_insights) == 3


def test_validation_evidence_completeness():
    validator = InsightValidationFramework()
    classifier = InsightClassifier()
    ctx = ConversationInsightContext(conversation_id="conv-1")

    # Empty evidence
    invalid_ev = InsightEvidence(extraction_method="INVALID", confidence=0.5)
    ctx.raw_risks = [
        RiskInsight(
            category=InsightCategory.MISSING_INFORMATION,
            title="Risk with no evidence",
            description="Lacks lineage",
            evidence=invalid_ev,
        )
    ]
    classifier.classify_and_harmonize(ctx)
    errors = validator.validate_context(ctx)

    assert len(errors) > 0
    assert "lacks mandatory supporting evidence" in errors[0]


def test_validation_forbidden_boundary_keys():
    validator = InsightValidationFramework()
    classifier = InsightClassifier()
    ctx = ConversationInsightContext(conversation_id="conv-1")

    ev = InsightEvidence(source_message_ids=["msg-1"], extraction_method="TEST")
    ctx.raw_risks = [
        RiskInsight(
            category=InsightCategory.BUDGET_GAP,
            title="Leaked Key Risk",
            description="Testing forbidden key guard",
            evidence=ev,
            metadata={"lead_score": 95, "recommendation_action": "CALL_NOW"},
        )
    ]
    classifier.classify_and_harmonize(ctx)
    errors = validator.validate_context(ctx)

    assert len(errors) >= 2
    assert any("forbidden architectural key" in e for e in errors)


def test_validation_cross_workspace_isolation():
    validator = InsightValidationFramework()
    ws_1 = uuid.uuid4()
    ws_2 = uuid.uuid4()

    analysis = create_mock_analysis_result(workspace_id=ws_1)
    timeline = create_mock_timeline(workspace_id=ws_2)

    ctx = ConversationInsightContext(analysis_result=analysis, timeline=timeline)
    errors = validator.validate_context(ctx)

    assert any("Cross-workspace contamination" in e for e in errors)


def test_deduplication():
    validator = InsightValidationFramework()
    classifier = InsightClassifier()
    ctx = ConversationInsightContext(conversation_id="conv-1")

    ev = InsightEvidence(source_message_ids=["msg-1"], extraction_method="TEST")
    r1 = RiskInsight(category=InsightCategory.BUDGET_GAP, title="Budget Gap", description="Details", evidence=ev)
    r2 = RiskInsight(category=InsightCategory.BUDGET_GAP, title="Budget Gap", description="Details", evidence=ev)

    ctx.raw_risks = [r1, r2]
    classifier.classify_and_harmonize(ctx)
    assert len(ctx.all_insights) == 2

    validator.deduplicate_insights(ctx)
    assert len(ctx.classified_risks) == 1
    assert len(ctx.all_insights) == 1
