"""
Tests for IntentClassificationValidator and Zero-Mutation Architectural Guardrails.
"""

import uuid
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassifiedIntent,
    ClassificationMethod,
    IntentCategory,
    IntentEvidence,
    IntentRelationship,
    IntentRelationshipType,
)
from app.domain.intents.classification.validation import IntentClassificationValidator


def _make_intent(workspace_id=None, conv_id="conv_val", metadata=None) -> ClassifiedIntent:
    return ClassifiedIntent(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        business_category=IntentCategory.COMMERCIAL,
        business_domain=BusinessDomain.CROSS_INDUSTRY,
        business_process="SALES_QUALIFICATION",
        taxonomy_path="commercial.pricing_inquiry",
        confidence=0.9,
        classification_method=ClassificationMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["pricing"]),
        metadata=metadata or {},
    )


def test_validator_detects_forbidden_metadata_keys():
    validator = IntentClassificationValidator()

    # Create intent with forbidden downstream key 'sentiment'
    intent_invalid = _make_intent(metadata={"sentiment": "positive", "legitimate_key": "val"})

    context = IntentClassificationContext(conversation_id="conv_val")
    context.classified_intents = [intent_invalid]

    is_valid = validator.validate(context)
    assert not is_valid
    assert len(context.validation_errors) == 1
    assert "Forbidden key 'sentiment'" in context.validation_errors[0]


def test_validator_detects_workspace_isolation_breach():
    validator = IntentClassificationValidator()
    ws_1 = uuid.uuid4()
    ws_2 = uuid.uuid4()

    # Context has ws_1, but intent belongs to ws_2
    intent_breach = _make_intent(workspace_id=ws_2)

    context = IntentClassificationContext(conversation_id="conv_val", workspace_id=ws_1)
    context.classified_intents = [intent_breach]

    is_valid = validator.validate(context)
    assert not is_valid
    assert any("Workspace mismatch" in err for err in context.validation_errors)


def test_validator_detects_self_referencing_relationship():
    validator = IntentClassificationValidator()
    i1 = _make_intent()

    context = IntentClassificationContext(conversation_id="conv_val")
    context.classified_intents = [i1]

    # Add self-referencing relationship
    rel_self = IntentRelationship(
        source_intent_id=i1.classified_intent_id,
        target_intent_id=i1.classified_intent_id,
        relationship_type=IntentRelationshipType.DEPENDENT_INTENT,
        confidence=0.8,
    )
    context.relationships = [rel_self]

    is_valid = validator.validate(context)
    assert not is_valid
    assert any("self-referencing" in err for err in context.validation_errors)
