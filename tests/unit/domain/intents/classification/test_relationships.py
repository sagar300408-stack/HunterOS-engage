"""
Tests for IntentRelationshipRuleRegistry and relationship evaluation.
"""

import uuid
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassifiedIntent,
    ClassificationMethod,
    IntentCategory,
    IntentEvidence,
    IntentRelationshipType,
)
from app.domain.intents.classification.relationships.engine import IntentRelationshipEngine
from app.domain.intents.classification.relationships.registry import (
    IntentRelationshipRuleRegistry,
)


def _make_intent(category: IntentCategory, path: str, aliases: list = None) -> ClassifiedIntent:
    return ClassifiedIntent(
        conversation_id="conv_rel_test",
        business_category=category,
        business_domain=BusinessDomain.CROSS_INDUSTRY,
        business_process="TEST_PROC",
        taxonomy_path=path,
        aliases=aliases or [path],
        confidence=0.9,
        classification_method=ClassificationMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["sample snippet"]),
    )


def test_dependency_and_conflict_relationships():
    registry = IntentRelationshipRuleRegistry()
    engine = IntentRelationshipEngine(registry=registry)

    # Setup intents: Booking Interest (which depends on Pricing Inquiry), and Cancellation (which conflicts with Booking)
    i_booking = _make_intent(
        IntentCategory.COMMERCIAL,
        "commercial.booking_interest",
        aliases=["BOOKING_INTEREST"],
    )
    i_pricing = _make_intent(
        IntentCategory.COMMERCIAL,
        "commercial.pricing_inquiry",
        aliases=["PRICING_INQUIRY"],
    )
    i_cancel = _make_intent(
        IntentCategory.OPERATIONAL,
        "operational.cancellation",
        aliases=["CANCEL_SUBSCRIPTION"],
    )

    context = IntentClassificationContext(conversation_id="conv_rel_test")
    context.classified_intents = [i_booking, i_pricing, i_cancel]

    rels = engine.compute_relationships(context)

    # Check dependency: Booking depends on Pricing
    dep_rels = [r for r in rels if r.relationship_type == IntentRelationshipType.DEPENDENT_INTENT]
    assert len(dep_rels) >= 1
    assert dep_rels[0].source_intent_id == i_booking.classified_intent_id
    assert dep_rels[0].target_intent_id == i_pricing.classified_intent_id

    # Check conflict: Cancel conflicts with Booking
    conf_rels = [r for r in rels if r.relationship_type == IntentRelationshipType.CONFLICTING_INTENT]
    assert len(conf_rels) >= 1
