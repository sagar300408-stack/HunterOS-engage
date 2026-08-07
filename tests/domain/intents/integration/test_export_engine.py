"""
Unit Tests for Intent Export Engine Projections (Phase 2.3.5)
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
from app.domain.intents.evolution.models import (
    IntentEvolutionProvenance,
    IntentEvolutionResult,
    IntentHistory,
    IntentLifecycleState,
)
from app.domain.intents.integration.engines.export import IntentExportEngine
from app.domain.intents.integration.models import (
    CompositionProfileType,
)
from app.domain.intents.integration.platform import IntentIntelligencePlatform
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionDiagnostics,
    IntentDetectionProvenance,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.resolution.models import (
    DominantIntent,
    DominanceFactor,
    DominanceFactorType,
    IntentClusterType,
    IntentConflict,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentGraphProvenance,
    IntentNode,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
    ResolutionGroupStatus,
    ResolutionSeverity,
)


def test_export_engine_projections():
    iid = uuid.uuid4()
    platform = IntentIntelligencePlatform()
    exporter = IntentExportEngine()

    det = IntentDetectionResult(
        conversation_id="conv_export_test",
        workspace_id="ws_export",
        detected_intents=[
            DetectedIntent(
                intent_id=iid,
                intent_type=IntentType.COMMERCIAL_INQUIRY,
                category=IntentTaxonomyCategory.COMMERCIAL,
                confidence_score=0.92,
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

    ctx = platform.build_context(
        conversation_id="conv_export_test",
        entity_id="cust_export",
        workspace_id="ws_export",
        profile=CompositionProfileType.FULL,
        detection_result=det,
    )

    full_dto = exporter.to_full_dto(ctx)
    assert full_dto.context_id == ctx.context_id
    assert full_dto.conversation_id == "conv_export_test"
    assert full_dto.metadata.composition_profile == "FULL"

    dash_dto = exporter.to_dashboard_dto(ctx)
    assert dash_dto.context_id == ctx.context_id
    assert dash_dto.total_intents_detected == 1

    exec_dto = exporter.to_executive_dto(ctx)
    assert exec_dto.context_id == ctx.context_id
    assert exec_dto.strategic_takeaway is not None

    struct_dto = exporter.to_structured_dto(ctx)
    assert struct_dto.context_id == ctx.context_id
    assert len(struct_dto.intents_by_stage["DETECTION"]) == 1

    api_dto = exporter.to_standard_api_dto(ctx)
    assert api_dto.context_id == ctx.context_id
    assert len(api_dto.detected_intents) == 1
