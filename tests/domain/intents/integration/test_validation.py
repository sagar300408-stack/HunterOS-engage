"""
Unit Tests for Zero-Trust Validation in Intent Integration Layer (Phase 2.3.5)
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.classification.models import (
    BusinessCategory,
    BusinessDomain,
    ClassificationMethod,
    ClassifiedIntent,
    IntentClassificationProvenance,
    IntentClassificationResult,
    TaxonomyPath,
)
from app.domain.intents.integration.validation import IntentContextValidator
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionDiagnostics,
    IntentDetectionProvenance,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)


def test_validator_workspace_mismatch():
    validator = IntentContextValidator()

    det = IntentDetectionResult(
        conversation_id="conv_valid_1",
        workspace_id="ws_different",
        detected_intents=[],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=0,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(),
    )

    errors = validator.validate_inputs(
        conversation_id="conv_valid_1",
        entity_id="cust_valid",
        workspace_id="ws_target",
        detection_result=det,
    )

    assert len(errors) == 1
    assert "Workspace ID mismatch" in errors[0]


def test_validator_conversation_mismatch():
    validator = IntentContextValidator()

    cls = IntentClassificationResult(
        conversation_id="conv_different",
        workspace_id="ws_target",
        classified_intents=[],
        provenance=IntentClassificationProvenance(
            classification_engine_version="1.0.0",
            pipeline_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )

    errors = validator.validate_inputs(
        conversation_id="conv_target",
        entity_id="cust_valid",
        workspace_id="ws_target",
        classification_result=cls,
    )

    assert len(errors) == 1
    assert "Conversation ID mismatch" in errors[0]


def test_validator_missing_tenant_fields():
    validator = IntentContextValidator()

    errors = validator.validate_inputs(
        conversation_id="",
        entity_id="",
        workspace_id="",
    )

    assert len(errors) == 3
