"""
HunterOS Engage V1 - Tests for Insight Projection Views
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    ConversationInsight,
    ConversationInsightResult,
    InsightCategory,
    InsightDiagnostics,
    InsightEvidence,
    InsightMetadata,
    InsightPriority,
    InsightScopeType,
    InsightType,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.insight.views.registry import (
    InsightViewRegistry,
    default_insight_view_registry,
)


def _build_test_result():
    res_id = uuid.uuid4()
    conv_id = "conv-view-test"
    ev = InsightEvidence(
        source_message_ids=["msg-1"],
        source_event_ids=[uuid.uuid4()],
        fact_ids=[uuid.uuid4()],
        extraction_method="TEST",
        confidence=0.95,
    )

    risk = RiskInsight(
        category=InsightCategory.BUDGET_GAP,
        title="Severe Budget Shortfall",
        description="Buyer stated budget is only 1 Cr",
        impact_description="May drop out",
        priority=InsightPriority.CRITICAL,
        confidence=0.96,
        evidence=ev,
    )
    opp = OpportunityInsight(
        category=InsightCategory.UPSELL,
        title="Penthouse Interest",
        description="Expressed interest in top floor",
        value_potential="ASP upgrade",
        qualification_criteria=["High intent"],
        priority=InsightPriority.HIGH,
        confidence=0.92,
        evidence=ev,
    )
    act = ActionItemInsight(
        category=InsightCategory.REQUESTED_DOCUMENT,
        owner_type=ActionOwnerType.INTERNAL_TEAM,
        title="Dispatch Master Layout Brochure",
        description="Customer requested layout pdf",
        priority=InsightPriority.HIGH,
        confidence=0.94,
        evidence=ev,
    )

    metadata = InsightMetadata(
        insight_result_id=res_id,
        conversation_id=conv_id,
        scope_type=InsightScopeType.CONVERSATION,
        total_insights=3,
        total_risks=1,
        total_opportunities=1,
        total_action_items=1,
        critical_count=1,
        high_count=2,
        medium_count=0,
        low_count=0,
        category_distribution={"BUDGET_GAP": 1, "UPSELL": 1, "REQUESTED_DOCUMENT": 1},
        schema_version="1.0.0",
        generator_version="2.2.3",
        generated_at=datetime.now(timezone.utc),
    )

    diagnostics = InsightDiagnostics(
        pipeline_execution_time_ms=10.0,
        stage_timings_ms={},
        stages_executed=["Stage1"],
        warnings=[],
        validation_errors=[],
        is_valid=True,
    )

    unified = [
        ConversationInsight(
            insight_id=risk.risk_id,
            insight_type=InsightType.RISK,
            category=risk.category,
            title=risk.title,
            description=risk.description,
            priority=risk.priority,
            confidence=risk.confidence,
            evidence=risk.evidence,
        ),
        ConversationInsight(
            insight_id=opp.opportunity_id,
            insight_type=InsightType.OPPORTUNITY,
            category=opp.category,
            title=opp.title,
            description=opp.description,
            priority=opp.priority,
            confidence=opp.confidence,
            evidence=opp.evidence,
        ),
    ]

    return ConversationInsightResult(
        insight_result_id=res_id,
        conversation_id=conv_id,
        metadata=metadata,
        risks=[risk],
        opportunities=[opp],
        action_items=[act],
        all_insights=unified,
        diagnostics=diagnostics,
    )


def test_executive_view():
    result = _build_test_result()
    rendered = default_insight_view_registry.render_view("executive", result)

    assert rendered["view"] == "executive"
    assert rendered["health_status"] == "CRITICAL_ATTENTION_REQUIRED"
    assert len(rendered["critical_risk_alerts"]) == 1
    assert len(rendered["high_value_opportunities"]) == 1


def test_sales_view():
    result = _build_test_result()
    rendered = default_insight_view_registry.render_view("sales", result)

    assert rendered["view"] == "sales"
    assert len(rendered["commercial_opportunities"]) == 1
    assert len(rendered["budget_and_requirement_risks"]) == 1


def test_operations_view():
    result = _build_test_result()
    rendered = default_insight_view_registry.render_view("operations", result)

    assert rendered["view"] == "operations"
    assert len(rendered["document_fulfillment_queue"]) == 1


def test_audit_view():
    result = _build_test_result()
    rendered = default_insight_view_registry.render_view("audit", result)

    assert rendered["view"] == "audit"
    assert rendered["total_insights"] == 2
    assert "evidence" in rendered["insights"][0]
    assert rendered["insights"][0]["evidence"]["source_message_ids"] == ["msg-1"]


def test_unregistered_view_raises():
    result = _build_test_result()
    with pytest.raises(KeyError):
        default_insight_view_registry.render_view("non_existent_view", result)
