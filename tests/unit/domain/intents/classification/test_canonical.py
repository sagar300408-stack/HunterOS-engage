"""
Tests for CanonicalIntent model and IntentNormalizer.
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.canonical.normalizer import IntentNormalizer
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionMethod,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)


def test_intent_normalizer_from_detected_intent():
    normalizer = IntentNormalizer()
    conv_id = "conv_test_canonical_1"
    ws_id = uuid.uuid4()

    detected = DetectedIntent(
        conversation_id=conv_id,
        workspace_id=ws_id,
        customer_id="cust_123",
        intent_type=IntentType.PRICING_INQUIRY,
        taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
        business_importance=BusinessImportance.COMMERCIAL,
        title="  Pricing Inquiry for 3BHK Apartment  ",
        description="  Customer inquired about total cost and payment schedules.  ",
        confidence=0.88,
        detection_method=IntentDetectionMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(
            source_message_ids=["msg_1", "msg_2"],
            text_snippets=["How much is the 3BHK flat?"],
        ),
        metadata={"unit_type": "3BHK"},
    )

    canonical = normalizer.normalize(detected)

    assert isinstance(canonical, CanonicalIntent)
    assert canonical.original_intent_id == detected.intent_id
    assert canonical.conversation_id == conv_id
    assert canonical.workspace_id == ws_id
    assert canonical.customer_id == "cust_123"
    assert canonical.canonical_name == "pricing_inquiry"
    assert canonical.normalized_title == "pricing inquiry for 3bhk apartment"
    assert canonical.normalized_description == "customer inquired about total cost and payment schedules."
    assert canonical.confidence == 0.88
    assert canonical.evidence_message_ids == ["msg_1", "msg_2"]
    assert canonical.text_snippets == ["How much is the 3BHK flat?"]
    assert canonical.payload.category_raw == "Commercial"
    assert canonical.payload.importance_raw == "COMMERCIAL"
    assert canonical.metadata["unit_type"] == "3BHK"


def test_intent_normalizer_fallback_for_plain_object():
    normalizer = IntentNormalizer()

    class MockRawIntent:
        def __init__(self):
            self.id = uuid.uuid4()
            self.name = "CUSTOM_BOOKING_SLOT"
            self.title = "Booking Tour"
            self.confidence = 0.95

    raw = MockRawIntent()
    canonical = normalizer.normalize(raw)

    assert canonical.original_intent_id == raw.id
    assert canonical.canonical_name == "custom_booking_slot"
    assert canonical.normalized_title == "booking tour"
    assert canonical.confidence == 0.95
