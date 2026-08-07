"""
Unit Tests for Intent Context Graph Builder & Relational Navigation (Phase 2.3.5)
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
from app.domain.intents.integration.graph import IntentContextGraphBuilder
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


def test_context_graph_construction_and_navigation():
    iid1 = uuid.uuid4()
    iid2 = uuid.uuid4()

    det = IntentDetectionResult(
        conversation_id="conv_graph_test",
        workspace_id="ws_graph",
        detected_intents=[
            DetectedIntent(
                intent_id=iid1,
                intent_type=IntentType.COMMERCIAL_INQUIRY,
                category=IntentTaxonomyCategory.COMMERCIAL,
                confidence_score=0.95,
                business_importance=BusinessImportance.HIGH,
                supporting_evidence_message_ids=["msg_10"],
            ),
            DetectedIntent(
                intent_id=iid2,
                intent_type=IntentType.CANCEL_SERVICE,
                category=IntentTaxonomyCategory.SUPPORT,
                confidence_score=0.85,
                business_importance=BusinessImportance.CRITICAL,
                supporting_evidence_message_ids=["msg_11"],
            ),
        ],
        provenance=IntentDetectionProvenance(
            detection_engine_version="1.0.0",
            total_messages_analyzed=2,
            generated_at=datetime.now(timezone.utc),
        ),
        diagnostics=IntentDetectionDiagnostics(),
    )

    cls = IntentClassificationResult(
        conversation_id="conv_graph_test",
        workspace_id="ws_graph",
        classified_intents=[
            ClassifiedIntent(
                original_intent_id=iid1,
                business_category=BusinessCategory.COMMERCIAL,
                business_domain=BusinessDomain.REVENUE,
                business_process="Pricing Negotiation",
                taxonomy_path=TaxonomyPath(l1="COMMERCIAL", l2="PRICING", l3="ENTERPRISE"),
                confidence=0.95,
                classification_method=ClassificationMethod.RULE_BASED,
            ),
            ClassifiedIntent(
                original_intent_id=iid2,
                business_category=BusinessCategory.SUPPORT,
                business_domain=BusinessDomain.OPERATIONS,
                business_process="Account Cancellation",
                taxonomy_path=TaxonomyPath(l1="SUPPORT", l2="ACCOUNT", l3="CANCELLATION"),
                confidence=0.85,
                classification_method=ClassificationMethod.RULE_BASED,
            ),
        ],
        provenance=IntentClassificationProvenance(
            classification_engine_version="1.0.0",
            pipeline_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )

    evo = IntentEvolutionResult(
        conversation_id="conv_graph_test",
        workspace_id="ws_graph",
        intent_histories=[
            IntentHistory(
                intent_id=iid1,
                canonical_intent_name="Pricing Negotiation",
                current_state=IntentLifecycleState.ACTIVE,
                first_turn_index=1,
                last_turn_index=2,
                observation_count=2,
            ),
            IntentHistory(
                intent_id=iid2,
                canonical_intent_name="Account Cancellation",
                current_state=IntentLifecycleState.ESCALATED,
                first_turn_index=2,
                last_turn_index=2,
                observation_count=1,
            ),
        ],
        provenance=IntentEvolutionProvenance(
            evolution_engine_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
        ),
    )

    node1 = IntentNode(
        intent_id=iid1,
        canonical_name="Pricing Negotiation",
        raw_intent_type="COMMERCIAL_INQUIRY",
        confidence=0.95,
        lifecycle_state="ACTIVE",
    )
    node2 = IntentNode(
        intent_id=iid2,
        canonical_name="Account Cancellation",
        raw_intent_type="CANCEL_SERVICE",
        confidence=0.85,
        lifecycle_state="ESCALATED",
    )

    conflict = IntentConflict(
        conflict_id=uuid.uuid4(),
        intent_ids=[iid1, iid2],
        conflict_type=IntentConflictType.MUTUALLY_EXCLUSIVE,
        severity=ResolutionSeverity.HIGH,
        description="Negotiating pricing vs cancellation",
    )
    dep = IntentDependency(
        dependency_id=uuid.uuid4(),
        source_intent_id=iid2,
        target_intent_id=iid1,
        dependency_type=IntentDependencyType.BLOCKS,
        is_blocking=True,
        reason="Pricing must resolve first",
    )

    res = MultiIntentResolutionResult(
        conversation_id="conv_graph_test",
        workspace_id="ws_graph",
        resolution_graph=IntentResolutionGraph(
            graph_id=uuid.uuid4(),
            nodes={str(iid1): node1, str(iid2): node2},
            conflicts=[conflict],
            dependencies=[dep],
        ),
        resolved_groups=[
            IntentResolutionGroup(
                group_id=uuid.uuid4(),
                name="Group 1",
                cluster_type=IntentClusterType.CO_OCCURRING,
                dominant_intent=DominantIntent(intent_id=iid1, canonical_name="Pricing Negotiation", dominance_score=0.9),
                supporting_intents=[node2],
                status=ResolutionGroupStatus.ACTIVE,
            )
        ],
        provenance=IntentGraphProvenance(
            resolution_engine_version="1.0.0",
            pipeline_version="1.0.0",
            rules_evaluated=[],
            generated_at=datetime.now(timezone.utc),
        ),
    )

    builder = IntentContextGraphBuilder()
    graph = builder.build_graph(
        detection_result=det,
        classification_result=cls,
        evolution_result=evo,
        resolution_result=res,
    )

    # 4 subsystems * 2 intents = 8 nodes
    assert len(graph.nodes) == 8
    # Links: 2 (DET->CLS) + 2 (CLS->EVO) + 2 (EVO->RES) + 1 (CONFLICT) + 1 (DEPENDENCY) = 8 links
    assert len(graph.links) >= 8

    lineage = graph.get_lineage(str(iid1))
    assert len(lineage) == 4
    subsystems = [n.subsystem for n in lineage]
    assert subsystems == ["DETECTION", "CLASSIFICATION", "EVOLUTION", "RESOLUTION"]

    conflicts = graph.get_conflicts(str(iid1))
    assert len(conflicts) == 1
    assert conflicts[0].intent_name == "Account Cancellation"

    deps = graph.get_dependencies(str(iid2))
    assert len(deps) == 1
    assert deps[0].intent_name == "Pricing Negotiation"
