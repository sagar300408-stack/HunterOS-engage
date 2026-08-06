"""
HunterOS Engage V1 - Tests for Insight Domain Models
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


def test_insight_evidence_model():
    ev = InsightEvidence(
        source_message_ids=["msg-1", "msg-2"],
        source_event_ids=[uuid.uuid4()],
        fact_ids=[uuid.uuid4()],
        topics=["Budgeting", "3BHK"],
        text_snippets=["Budget is 2.5 Cr"],
        extraction_method="DETERMINISTIC_TEST",
        confidence=0.95,
    )
    assert len(ev.source_message_ids) == 2
    assert len(ev.topics) == 2
    assert ev.confidence == 0.95


def test_risk_insight_model():
    ev = InsightEvidence(
        source_message_ids=["msg-1"],
        extraction_method="TEST",
    )
    risk = RiskInsight(
        category=InsightCategory.BUDGET_GAP,
        title="Budget Shortfall",
        description="Buyer budget below minimum unit pricing",
        impact_description="Customer may churn",
        priority=InsightPriority.HIGH,
        confidence=0.92,
        evidence=ev,
    )
    assert risk.risk_id is not None
    assert risk.category == InsightCategory.BUDGET_GAP
    assert risk.priority == InsightPriority.HIGH


def test_opportunity_insight_model():
    ev = InsightEvidence(
        source_message_ids=["msg-1"],
        extraction_method="TEST",
    )
    opp = OpportunityInsight(
        category=InsightCategory.UPSELL,
        title="Penthouse Interest",
        description="Buyer asked about top-floor penthouses",
        value_potential="ASP upgrade by 40%",
        qualification_criteria=["High purchasing capacity"],
        priority=InsightPriority.HIGH,
        confidence=0.95,
        evidence=ev,
    )
    assert opp.category == InsightCategory.UPSELL
    assert opp.qualification_criteria == ["High purchasing capacity"]


def test_action_item_insight_model():
    ev = InsightEvidence(
        source_message_ids=["msg-1"],
        extraction_method="TEST",
    )
    action = ActionItemInsight(
        category=InsightCategory.INTERNAL_TEAM_ACTION,
        owner_type=ActionOwnerType.INTERNAL_TEAM,
        title="Send Pricing Sheet",
        description="Dispatch 3BHK rate matrix",
        due_date_hint="Tomorrow 2 PM",
        priority=InsightPriority.MEDIUM,
        confidence=0.90,
        evidence=ev,
    )
    assert action.owner_type == ActionOwnerType.INTERNAL_TEAM
    assert action.due_date_hint == "Tomorrow 2 PM"


def test_conversation_insight_result_serialization():
    conv_id = "conv-test-123"
    res_id = uuid.uuid4()
    ev = InsightEvidence(source_message_ids=["msg-1"], extraction_method="TEST")
    
    risk = RiskInsight(
        category=InsightCategory.MISSING_INFORMATION,
        title="Missing Contact",
        description="No phone provided",
        evidence=ev,
    )
    opp = OpportunityInsight(
        category=InsightCategory.MEETING,
        title="Site Visit Possible",
        description="Ready for visit",
        evidence=ev,
    )
    act = ActionItemInsight(
        category=InsightCategory.CUSTOMER_ACTION,
        owner_type=ActionOwnerType.CUSTOMER,
        title="Review floor plan",
        description="Customer to check layout",
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
        critical_count=0,
        high_count=0,
        medium_count=3,
        low_count=0,
        category_distribution={"MISSING_INFORMATION": 1, "MEETING": 1, "CUSTOMER_ACTION": 1},
        schema_version="1.0.0",
        generator_version="2.2.3",
        generated_at=datetime.now(timezone.utc),
    )

    diagnostics = InsightDiagnostics(
        pipeline_execution_time_ms=12.5,
        stage_timings_ms={"LoadArtifactsStage": 1.0},
        stages_executed=["LoadArtifactsStage"],
        warnings=[],
        validation_errors=[],
        is_valid=True,
    )

    result = ConversationInsightResult(
        insight_result_id=res_id,
        conversation_id=conv_id,
        metadata=metadata,
        risks=[risk],
        opportunities=[opp],
        action_items=[act],
        all_insights=[],
        diagnostics=diagnostics,
    )

    d = result.model_dump()
    assert d["conversation_id"] == conv_id
    assert d["metadata"]["total_risks"] == 1
    assert len(d["risks"]) == 1
