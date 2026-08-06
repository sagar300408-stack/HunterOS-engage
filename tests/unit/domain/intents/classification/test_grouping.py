"""
Tests for IntentGroupingEngine.
"""

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.grouping.engine import IntentGroupingEngine
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassifiedIntent,
    ClassificationMethod,
    IntentCategory,
    IntentEvidence,
    IntentGroupType,
)


def _make_intent(category: IntentCategory, path: str, conf: float) -> ClassifiedIntent:
    return ClassifiedIntent(
        conversation_id="conv_grp_test",
        business_category=category,
        business_domain=BusinessDomain.CROSS_INDUSTRY,
        business_process="PROC",
        taxonomy_path=path,
        confidence=conf,
        classification_method=ClassificationMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["test"]),
    )


def test_intent_grouping_by_category():
    engine = IntentGroupingEngine()

    c1 = _make_intent(IntentCategory.COMMERCIAL, "commercial.pricing_inquiry", 0.95)
    c2 = _make_intent(IntentCategory.COMMERCIAL, "commercial.booking_interest", 0.85)
    o1 = _make_intent(IntentCategory.OPERATIONAL, "operational.meeting_request", 0.90)

    context = IntentClassificationContext(conversation_id="conv_grp_test")
    context.classified_intents = [c1, c2, o1]

    groups = engine.group_intents(context)

    assert len(groups) == 2
    comm_group = next(g for g in groups if g.group_type == IntentGroupType.COMMERCIAL)
    assert len(comm_group.intent_ids) == 2
    assert comm_group.primary_intent_id == c2.classified_intent_id or comm_group.primary_intent_id == c1.classified_intent_id
    assert comm_group.aggregate_confidence == 0.90
