"""
Tests for Intent Classification 8-Stage Pipeline and CanonicalIntentAPIv1.
"""

import uuid
import pytest

from app.domain.intents.classification.api import CanonicalIntentAPIv1
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
    IntentClassificationResult,
)
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionMethod,
    IntentDetectionResult,
    IntentDiagnostics,
    IntentEvidence,
    IntentMetadata,
    IntentProvenance,
    IntentTaxonomyCategory,
    IntentType,
)


def test_classification_pipeline_and_api_end_to_end():
    api = CanonicalIntentAPIv1()

    conv_id = f"conv_test_pipeline_{uuid.uuid4().hex[:8]}"
    ws_id = uuid.uuid4()

    # Create synthetic detected intents
    detected_1 = DetectedIntent(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust_pipeline_1",
        intent_type=IntentType.PRICING_INQUIRY,
        taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
        business_importance=BusinessImportance.COMMERCIAL,
        title="Pricing question for flat",
        description="Inquired about standard discounts and payment terms.",
        confidence=0.90,
        detection_method=IntentDetectionMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["What is the total price?"]),
    )
    detected_2 = DetectedIntent(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust_pipeline_1",
        intent_type=IntentType.SCHEDULE_MEETING,
        taxonomy_category=IntentTaxonomyCategory.OPERATIONAL,
        business_importance=BusinessImportance.OPERATIONAL,
        title="Schedule sample flat site visit",
        description="Customer wants to book a physical visit tomorrow.",
        confidence=0.88,
        detection_method=IntentDetectionMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(text_snippets=["Can I visit the property tomorrow?"]),
    )

    det_result = IntentDetectionResult(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust_pipeline_1",
        intents=[detected_1, detected_2],
        metadata=IntentMetadata(
            conversation_id=conv_id,
            total_intents=2,
            dominant_category=IntentTaxonomyCategory.COMMERCIAL,
            primary_intent=IntentType.PRICING_INQUIRY,
        ),
        diagnostics=IntentDiagnostics(is_valid=True),
    )

    # Classify via CanonicalIntentAPIv1
    result = api.classify_conversation(
        conversation_id=conv_id,
        detection_result=det_result,
        workspace_id=ws_id,
        customer_id="cust_pipeline_1",
    )

    assert isinstance(result, IntentClassificationResult)
    assert result.conversation_id == conv_id
    assert len(result.classified_intents) == 2
    assert result.metadata.total_classified_intents == 2
    assert result.diagnostics.is_valid is True

    # Verify CQRS lookup
    saved = api.get_latest_classification_for_conversation(conv_id)
    assert saved is not None
    assert saved.classification_id == result.classification_id

    # Verify View Projection
    exec_view = api.get_view(conv_id, "executive")
    assert exec_view is not None
    assert exec_view["summary"]["total_intents_classified"] == 2

    # Verify Analytics
    analytics = api.run_analytics(workspace_id=ws_id)
    assert analytics.total_classifications >= 1
    assert analytics.total_classified_intents >= 2
