"""
Tests for Multi-Perspective Classification Views.
"""

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassifiedIntent,
    ClassificationMethod,
    IntentCategory,
    IntentEvidence,
    IntentGroup,
    IntentGroupType,
    IntentRelationship,
    IntentRelationshipType,
)
from app.domain.intents.classification.stages.generate_result import (
    GenerateClassificationResultStage,
)
from app.domain.intents.classification.views.audit import AuditClassificationView
from app.domain.intents.classification.views.executive import (
    ExecutiveClassificationView,
)
from app.domain.intents.classification.views.operations import (
    OperationsClassificationView,
)
from app.domain.intents.classification.views.sales import SalesClassificationView


def test_views_generation():
    # Construct a sample classification result
    i1 = ClassifiedIntent(
        conversation_id="conv_views_1",
        business_category=IntentCategory.COMMERCIAL,
        business_domain=BusinessDomain.REAL_ESTATE,
        business_process="LEAD_CAPTURE",
        taxonomy_path="commercial.pricing_inquiry",
        confidence=0.92,
        classification_method=ClassificationMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["price details"]),
    )
    i2 = ClassifiedIntent(
        conversation_id="conv_views_1",
        business_category=IntentCategory.OPERATIONAL,
        business_domain=BusinessDomain.REAL_ESTATE,
        business_process="APPOINTMENT_SCHEDULING",
        taxonomy_path="operational.site_visit",
        confidence=0.88,
        classification_method=ClassificationMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["visit flat"]),
    )
    rel = IntentRelationship(
        source_intent_id=i2.classified_intent_id,
        target_intent_id=i1.classified_intent_id,
        relationship_type=IntentRelationshipType.DEPENDENT_INTENT,
        confidence=0.8,
    )
    grp = IntentGroup(
        name="Real Estate Operations",
        group_type=IntentGroupType.CATEGORY_CLUSTER,
        category=IntentCategory.OPERATIONAL,
        intent_ids=[i2.classified_intent_id],
        primary_intent_id=i2.classified_intent_id,
        aggregate_confidence=0.88,
    )

    ctx = IntentClassificationContext(conversation_id="conv_views_1")
    ctx.classified_intents = [i1, i2]
    ctx.relationships = [rel]
    ctx.groups = [grp]

    result = GenerateClassificationResultStage().execute(ctx)

    # 1. Executive View
    exec_view = ExecutiveClassificationView().generate(result)
    assert exec_view["view_type"] == "EXECUTIVE"
    assert exec_view["summary"]["total_intents_classified"] == 2
    assert "COMMERCIAL" in exec_view["category_breakdown"]

    # 2. Sales View
    sales_view = SalesClassificationView().generate(result)
    assert sales_view["view_type"] == "SALES"
    assert sales_view["commercial_signals"]["commercial_intent_count"] == 1

    # 3. Operations View
    ops_view = OperationsClassificationView().generate(result)
    assert ops_view["view_type"] == "OPERATIONS"
    assert ops_view["operational_summary"]["total_operational_intents"] == 1
    assert ops_view["operational_summary"]["has_site_visit"] is True

    # 4. Audit View
    audit_view = AuditClassificationView().generate(result)
    assert audit_view["view_type"] == "AUDIT"
    assert audit_view["architectural_compliance"]["zero_memory_mutations"] is True
