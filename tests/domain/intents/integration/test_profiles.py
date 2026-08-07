"""
Unit Tests for all 10 Composition Profiles (Phase 2.3.5)
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
from app.domain.intents.integration.models import CompositionProfileType
from app.domain.intents.integration.platform import IntentIntelligencePlatform
from app.domain.intents.integration.profiles import (
    AuditProfile,
    ClassificationProfile,
    CustomProfile,
    EvolutionProfile,
    ExecutiveProfile,
    FullProfile,
    MinimalProfile,
    OperationsProfile,
    ResolutionProfile,
    SalesProfile,
)
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
    IntentGraphProvenance,
    IntentNode,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
    ResolutionGroupStatus,
)


@pytest.fixture
def full_pipeline_fixtures():
    iid1 = uuid.uuid4()
    det = IntentDetectionResult(
        conversation_id="conv_profiles_test",
        workspace_id="ws_profiles",
        detected_intents=[
            DetectedIntent(
                intent_id=iid1,
                intent_type=IntentType.COMMERCIAL_INQUIRY,
                category=IntentTaxonomyCategory.COMMERCIAL,
                confidence_score=0.94,
                business_importance=BusinessImportance.HIGH,
            )
        ],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=1,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(rules_executed=["RuleCommercial"]),
    )
    cls = IntentClassificationResult(
        conversation_id="conv_profiles_test",
        workspace_id="ws_profiles",
        classified_intents=[
            ClassifiedIntent(
                original_intent_id=iid1,
                business_category=BusinessCategory.COMMERCIAL,
                business_domain=BusinessDomain.REVENUE,
                business_process="Pricing Negotiation",
                taxonomy_path=TaxonomyPath(l1="COMMERCIAL", l2="PRICING", l3="ENTERPRISE"),
                confidence=0.94,
                classification_method=ClassificationMethod.RULE_BASED,
            )
        ],
        provenance=IntentClassificationProvenance(
            classification_engine_version="1.0.0",
            pipeline_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    evo = IntentEvolutionResult(
        conversation_id="conv_profiles_test",
        workspace_id="ws_profiles",
        intent_histories=[
            IntentHistory(
                intent_id=iid1,
                canonical_intent_name="Pricing Negotiation",
                current_state=IntentLifecycleState.ACTIVE,
                first_turn_index=1,
                last_turn_index=1,
            )
        ],
        provenance=IntentEvolutionProvenance(
            evolution_engine_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    node = IntentNode(
        intent_id=iid1,
        canonical_name="Pricing Negotiation",
        raw_intent_type="COMMERCIAL_INQUIRY",
        confidence=0.94,
        lifecycle_state="ACTIVE",
    )
    dom = DominantIntent(
        intent_id=iid1,
        canonical_name=node.canonical_name,
        dominance_score=0.9,
    )
    res = MultiIntentResolutionResult(
        conversation_id="conv_profiles_test",
        workspace_id="ws_profiles",
        resolution_graph=IntentResolutionGraph(
            graph_id=uuid.uuid4(),
            nodes={str(iid1): node},
        ),
        resolved_groups=[
            IntentResolutionGroup(
                group_id=uuid.uuid4(),
                name="Commercial Group",
                cluster_type=IntentClusterType.CO_OCCURRING,
                dominant_intent=dom,
                supporting_intents=[],
                status=ResolutionGroupStatus.ACTIVE,
            )
        ],
        provenance=IntentGraphProvenance(
            resolution_engine_version="1.0.0",
            pipeline_version="1.0.0",
            rules_evaluated=["DominanceRule"],
            generated_at=datetime.now(timezone.utc),
        ),
    )
    return det, cls, evo, res


def test_all_10_profiles(full_pipeline_fixtures):
    det, cls, evo, res = full_pipeline_fixtures
    platform = IntentIntelligencePlatform()

    profiles_to_test = [
        CompositionProfileType.MINIMAL,
        CompositionProfileType.CLASSIFICATION,
        CompositionProfileType.EVOLUTION,
        CompositionProfileType.RESOLUTION,
        CompositionProfileType.FULL,
        CompositionProfileType.EXECUTIVE,
        CompositionProfileType.SALES,
        CompositionProfileType.OPERATIONS,
        CompositionProfileType.AUDIT,
        CompositionProfileType.CUSTOM,
    ]

    for prof in profiles_to_test:
        ctx = platform.build_context(
            conversation_id="conv_profiles_test",
            entity_id="cust_test",
            workspace_id="ws_profiles",
            profile=prof,
            detection_result=det,
            classification_result=cls,
            evolution_result=evo,
            resolution_result=res,
            custom_filters={"min_confidence": 0.8},
        )
        assert ctx.metadata.composition_profile == prof.value
        assert ctx.diagnostics.is_valid is True

        if prof == CompositionProfileType.MINIMAL:
            assert ctx.detection_result is not None
            assert ctx.classification_result is None
        elif prof == CompositionProfileType.EXECUTIVE:
            assert ctx.executive_view is not None
        elif prof == CompositionProfileType.SALES:
            assert ctx.sales_view is not None
        elif prof == CompositionProfileType.OPERATIONS:
            assert ctx.operations_view is not None
        elif prof == CompositionProfileType.AUDIT:
            assert ctx.audit_view is not None
        elif prof == CompositionProfileType.CUSTOM:
            assert ctx.custom_view is not None
            assert len(ctx.custom_view.filtered_intents) >= 1
