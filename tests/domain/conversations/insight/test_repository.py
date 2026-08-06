"""
HunterOS Engage V1 - Tests for Insight Repository
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    ConversationInsightResult,
    InsightCategory,
    InsightDiagnostics,
    InsightEvidence,
    InsightMetadata,
    InsightPriority,
    InsightScopeType,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.insight.repository import InMemoryInsightRepository


def _mock_result(conv_id="conv-1", customer_id="cust-1"):
    res_id = uuid.uuid4()
    ev = InsightEvidence(source_message_ids=["msg-1"], extraction_method="TEST")

    risk = RiskInsight(
        category=InsightCategory.BUDGET_GAP,
        title="Budget Gap",
        description="Detail",
        priority=InsightPriority.HIGH,
        evidence=ev,
    )
    opp = OpportunityInsight(
        category=InsightCategory.UPSELL,
        title="Penthouse",
        description="Detail",
        priority=InsightPriority.MEDIUM,
        evidence=ev,
    )
    act = ActionItemInsight(
        category=InsightCategory.CUSTOMER_ACTION,
        owner_type=ActionOwnerType.CUSTOMER,
        title="Send ID",
        description="Detail",
        priority=InsightPriority.HIGH,
        evidence=ev,
    )

    metadata = InsightMetadata(
        insight_result_id=res_id,
        conversation_id=conv_id,
        customer_id=customer_id,
        scope_type=InsightScopeType.CONVERSATION,
        total_insights=3,
        total_risks=1,
        total_opportunities=1,
        total_action_items=1,
        critical_count=0,
        high_count=2,
        medium_count=1,
        low_count=0,
        category_distribution={},
        schema_version="1.0.0",
        generator_version="2.2.3",
        generated_at=datetime.now(timezone.utc),
    )

    diagnostics = InsightDiagnostics(
        pipeline_execution_time_ms=5.0,
        stage_timings_ms={},
        stages_executed=[],
        warnings=[],
        validation_errors=[],
        is_valid=True,
    )

    return ConversationInsightResult(
        insight_result_id=res_id,
        conversation_id=conv_id,
        customer_id=customer_id,
        metadata=metadata,
        risks=[risk],
        opportunities=[opp],
        action_items=[act],
        all_insights=[],
        diagnostics=diagnostics,
    )


def test_repository_save_and_query():
    repo = InMemoryInsightRepository()
    r1 = _mock_result("conv-1", "cust-1")
    repo.save(r1)

    assert repo.get_by_id(r1.insight_result_id) is not None
    assert repo.get_latest_by_conversation("conv-1") == r1
    assert len(repo.list_by_conversation("conv-1")) == 1
    assert len(repo.list_by_customer("cust-1")) == 1


def test_repository_filters():
    repo = InMemoryInsightRepository()
    r = _mock_result("conv-1", "cust-1")
    repo.save(r)

    # Risk filter
    risks_high = repo.get_risks("conv-1", priority=InsightPriority.HIGH)
    assert len(risks_high) == 1
    risks_crit = repo.get_risks("conv-1", priority=InsightPriority.CRITICAL)
    assert len(risks_crit) == 0

    # Opp filter
    opps_upsell = repo.get_opportunities("conv-1", category=InsightCategory.UPSELL)
    assert len(opps_upsell) == 1
    opps_meeting = repo.get_opportunities("conv-1", category=InsightCategory.MEETING)
    assert len(opps_meeting) == 0

    # Action filter
    acts_high = repo.get_action_items("conv-1", priority=InsightPriority.HIGH)
    assert len(acts_high) == 1


def test_repository_delete():
    repo = InMemoryInsightRepository()
    r = _mock_result("conv-1", "cust-1")
    repo.save(r)

    assert repo.delete(r.insight_result_id) is True
    assert repo.get_by_id(r.insight_result_id) is None
    assert repo.get_latest_by_conversation("conv-1") is None
    assert repo.delete(r.insight_result_id) is False
