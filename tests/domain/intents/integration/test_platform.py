"""
Unit & Integration Tests for Intent Intelligence Platform (Phase 2.3.5)
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
    IntentObservation,
    TurnTrajectory,
)
from app.domain.intents.integration.models import (
    CompositionProfileType,
    IntentIntelligenceContext,
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


@pytest.fixture
def mock_detection_result():
    intent1 = DetectedIntent(
        intent_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        intent_type=IntentType.COMMERCIAL_INQUIRY,
        category=IntentTaxonomyCategory.COMMERCIAL,
        confidence_score=0.92,
        business_importance=BusinessImportance.HIGH,
        supporting_evidence_message_ids=["msg_1"],
    )
    intent2 = DetectedIntent(
        intent_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        intent_type=IntentType.CANCEL_SERVICE,
        category=IntentTaxonomyCategory.SUPPORT,
        confidence_score=0.88,
        business_importance=BusinessImportance.CRITICAL,
        supporting_evidence_message_ids=["msg_2"],
    )
    return IntentDetectionResult(
        conversation_id="conv_test_100",
        workspace_id="ws_main",
        detected_intents=[intent1, intent2],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=2,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(rules_executed=["RuleCommercial", "RuleCancel"]),
    )


@pytest.fixture
def mock_classification_result():
    c1 = ClassifiedIntent(
        original_intent_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        business_category=BusinessCategory.COMMERCIAL,
        business_domain=BusinessDomain.REVENUE,
        business_process="Pricing Negotiation",
        taxonomy_path=TaxonomyPath(l1="COMMERCIAL", l2="PRICING", l3="ENTERPRISE"),
        confidence=0.95,
        classification_method=ClassificationMethod.RULE_BASED,
    )
    c2 = ClassifiedIntent(
        original_intent_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        business_category=BusinessCategory.SUPPORT,
        business_domain=BusinessDomain.OPERATIONS,
        business_process="Account Cancellation",
        taxonomy_path=TaxonomyPath(l1="SUPPORT", l2="ACCOUNT", l3="CANCELLATION"),
        confidence=0.91,
        classification_method=ClassificationMethod.RULE_BASED,
    )
    return IntentClassificationResult(
        conversation_id="conv_test_100",
        workspace_id="ws_main",
        classified_intents=[c1, c2],
        provenance=IntentClassificationProvenance(
            classification_engine_version="1.0.0",
            pipeline_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture
def mock_evolution_result():
    h1 = IntentHistory(
        intent_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        canonical_intent_name="Pricing Negotiation",
        current_state=IntentLifecycleState.ACTIVE,
        first_turn_index=1,
        last_turn_index=2,
        observation_count=2,
    )
    h2 = IntentHistory(
        intent_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        canonical_intent_name="Account Cancellation",
        current_state=IntentLifecycleState.ESCALATED,
        first_turn_index=2,
        last_turn_index=2,
        observation_count=1,
    )
    return IntentEvolutionResult(
        conversation_id="conv_test_100",
        workspace_id="ws_main",
        intent_histories=[h1, h2],
        provenance=IntentEvolutionProvenance(
            evolution_engine_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture
def mock_resolution_result():
    node1 = IntentNode(
        intent_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        canonical_name="Pricing Negotiation",
        raw_intent_type="COMMERCIAL_INQUIRY",
        confidence=0.95,
        lifecycle_state="ACTIVE",
    )
    node2 = IntentNode(
        intent_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        canonical_name="Account Cancellation",
        raw_intent_type="CANCEL_SERVICE",
        confidence=0.91,
        lifecycle_state="ESCALATED",
    )

    conflict = IntentConflict(
        conflict_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        intent_ids=[node1.intent_id, node2.intent_id],
        conflict_type=IntentConflictType.MUTUALLY_EXCLUSIVE,
        severity=ResolutionSeverity.HIGH,
        description="Customer negotiating pricing while requesting cancellation.",
        resolution_hint="Escalate to senior account executive.",
    )

    dependency = IntentDependency(
        dependency_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        source_intent_id=node2.intent_id,
        target_intent_id=node1.intent_id,
        dependency_type=IntentDependencyType.BLOCKS,
        is_blocking=True,
        reason="Pricing agreement required before cancellation review.",
    )

    dom = DominantIntent(
        intent_id=node1.intent_id,
        canonical_name=node1.canonical_name,
        dominance_score=0.85,
        factors=[DominanceFactor(factor_type=DominanceFactorType.COMMERCIAL_VALUE, score=0.9, rationale="High revenue impact")],
    )

    group = IntentResolutionGroup(
        group_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        name="Commercial Retention Group",
        cluster_type=IntentClusterType.CO_OCCURRING,
        dominant_intent=dom,
        supporting_intents=[node2],
        status=ResolutionGroupStatus.ACTIVE,
    )

    res_graph = IntentResolutionGraph(
        graph_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        nodes={str(node1.intent_id): node1, str(node2.intent_id): node2},
        conflicts=[conflict],
        dependencies=[dependency],
    )

    return MultiIntentResolutionResult(
        conversation_id="conv_test_100",
        workspace_id="ws_main",
        resolution_graph=res_graph,
        resolved_groups=[group],
        provenance=IntentGraphProvenance(
            resolution_engine_version="1.0.0",
            pipeline_version="1.0.0",
            rules_evaluated=["DominanceRule", "ConflictRule"],
            generated_at=datetime.now(timezone.utc),
        ),
    )


def test_platform_full_integration(
    mock_detection_result,
    mock_classification_result,
    mock_evolution_result,
    mock_resolution_result,
):
    platform = IntentIntelligencePlatform()

    context = platform.build_context(
        conversation_id="conv_test_100",
        entity_id="cust_123",
        workspace_id="ws_main",
        profile=CompositionProfileType.FULL,
        detection_result=mock_detection_result,
        classification_result=mock_classification_result,
        evolution_result=mock_evolution_result,
        resolution_result=mock_resolution_result,
    )

    assert isinstance(context, IntentIntelligenceContext)
    assert context.conversation_id == "conv_test_100"
    assert context.entity_id == "cust_123"
    assert context.workspace_id == "ws_main"
    assert context.diagnostics.is_valid is True
    assert context.completeness_report.completeness_score == 1.0
    assert len(context.context_graph.nodes) > 0
    assert context.executive_view is not None
    assert context.sales_view is not None
    assert context.operations_view is not None
    assert context.audit_view is not None


def test_platform_projections_and_exports(
    mock_detection_result,
    mock_classification_result,
    mock_evolution_result,
    mock_resolution_result,
):
    platform = IntentIntelligencePlatform()

    platform.build_context(
        conversation_id="conv_test_100",
        entity_id="cust_123",
        workspace_id="ws_main",
        profile=CompositionProfileType.FULL,
        detection_result=mock_detection_result,
        classification_result=mock_classification_result,
        evolution_result=mock_evolution_result,
        resolution_result=mock_resolution_result,
    )

    exec_view = platform.get_executive_context("conv_test_100")
    assert exec_view is not None
    assert "Pricing Negotiation" in exec_view.strategic_focus

    sales_view = platform.get_sales_context("conv_test_100")
    assert sales_view is not None
    assert len(sales_view.buying_signals) > 0

    ops_view = platform.get_operations_context("conv_test_100")
    assert ops_view is not None
    assert ops_view.unresolved_dependencies_count >= 1

    dash_dto = platform.export_dashboard("conv_test_100")
    assert dash_dto is not None
    assert dash_dto.completeness_score == 1.0

    struct_dto = platform.export_structured("conv_test_100")
    assert struct_dto is not None
    assert "DETECTION" in struct_dto.intents_by_stage
