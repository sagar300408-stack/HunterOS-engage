"""
Unit Tests for Intent Context Assembler (Phase 2.3.5)
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
from app.domain.intents.integration.assembler import IntentContextAssembler
from app.domain.intents.integration.models import CompositionProfileType
from app.domain.intents.integration.profiles.minimal import MinimalProfile
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionDiagnostics,
    IntentDetectionProvenance,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)


def test_assembler_partial_artifacts():
    assembler = IntentContextAssembler()

    det = IntentDetectionResult(
        conversation_id="conv_partial",
        workspace_id="ws_main",
        detected_intents=[
            DetectedIntent(
                intent_id=uuid.uuid4(),
                intent_type=IntentType.REQUEST_DOCUMENT,
                category=IntentTaxonomyCategory.OPERATIONS,
                confidence_score=0.9,
                business_importance=BusinessImportance.MEDIUM,
            )
        ],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=1,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(),
    )

    ctx = assembler.assemble(
        conversation_id="conv_partial",
        entity_id="cust_456",
        workspace_id="ws_main",
        detection_result=det,
    )

    assert ctx.conversation_id == "conv_partial"
    assert ctx.detection_result is not None
    assert ctx.classification_result is None
    assert ctx.evolution_result is None
    assert ctx.resolution_result is None
    assert ctx.completeness_report.has_detection is True
    assert ctx.completeness_report.has_classification is False
    assert ctx.completeness_report.completeness_score == 0.25
    assert "CLASSIFICATION" in ctx.completeness_report.missing_modules
    assert ctx.diagnostics.is_valid is True


def test_assembler_with_minimal_profile():
    assembler = IntentContextAssembler()

    det = IntentDetectionResult(
        conversation_id="conv_min",
        workspace_id="ws_main",
        detected_intents=[
            DetectedIntent(
                intent_id=uuid.uuid4(),
                intent_type=IntentType.COMMERCIAL_INQUIRY,
                category=IntentTaxonomyCategory.COMMERCIAL,
                confidence_score=0.95,
                business_importance=BusinessImportance.HIGH,
            )
        ],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=1,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(),
    )

    ctx = assembler.assemble(
        conversation_id="conv_min",
        entity_id="cust_789",
        workspace_id="ws_main",
        detection_result=det,
        profile=MinimalProfile(),
    )

    assert ctx.metadata.composition_profile == CompositionProfileType.MINIMAL.value
    assert ctx.detection_result is not None
    assert ctx.classification_result is None
