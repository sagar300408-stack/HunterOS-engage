"""
Unit & integration tests for Multi-Intent Resolution Pipeline and Engine.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassificationDiagnostics,
    ClassificationMetadata,
    ClassificationMethod,
    ClassificationProvenance,
    ClassifiedIntent,
    IntentCategory,
    IntentClassificationResult,
)
from app.domain.intents.evolution.models import (
    EntityType,
    IntentHistory,
    IntentTimeline,
    IntentEvolutionResult,
    IntentLifecycleState,
)
from app.domain.intents.models import (
    DetectedIntent,
    IntentDetectionResult,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.resolution.engine import MultiIntentResolutionEngine
from app.domain.intents.resolution.pipeline import MultiIntentResolutionPipeline
from app.domain.intents.resolution.repository import ResolutionRepository


def test_multi_intent_pipeline_and_engine_full_flow():
    conv_id = "conv_1001"
    ws_id = uuid.uuid4()
    intent_id_demo = uuid.uuid4()
    intent_id_price = uuid.uuid4()
    intent_id_cancel = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 1. Mock Detection Result
    detection_result = IntentDetectionResult(
        conversation_id=conv_id,
        workspace_id=ws_id,
        intents=[
            DetectedIntent(
                intent_id=intent_id_demo,
                intent_type=IntentType.SCHEDULE_MEETING,
                taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
                confidence=0.92,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_1", "msg_2"]),
            ),
            DetectedIntent(
                intent_id=intent_id_price,
                intent_type=IntentType.PRICING_INQUIRY,
                taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
                confidence=0.88,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_3"]),
            ),
            DetectedIntent(
                intent_id=intent_id_cancel,
                intent_type=IntentType.CANCELLATION,
                taxonomy_category=IntentTaxonomyCategory.OPERATIONAL,
                confidence=0.80,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_4"]),
            ),
        ],
    )

    # 2. Mock Classification Result
    classification_result = IntentClassificationResult(
        conversation_id=conv_id,
        workspace_id=ws_id,
        classified_intents=[
            ClassifiedIntent(
                original_intent_id=intent_id_demo,
                conversation_id=conv_id,
                workspace_id=ws_id,
                business_category=IntentCategory.COMMERCIAL,
                business_domain=BusinessDomain.SAAS,
                business_process="SCHEDULE_DEMO",
                taxonomy_path="commercial.demo",
                confidence=0.95,
                classification_method=ClassificationMethod.RULE_BASED,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_1"]),
            ),
            ClassifiedIntent(
                original_intent_id=intent_id_price,
                conversation_id=conv_id,
                workspace_id=ws_id,
                business_category=IntentCategory.COMMERCIAL,
                business_domain=BusinessDomain.SAAS,
                business_process="PRICING_INQUIRY",
                taxonomy_path="commercial.pricing",
                confidence=0.90,
                classification_method=ClassificationMethod.RULE_BASED,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_3"]),
            ),
            ClassifiedIntent(
                original_intent_id=intent_id_cancel,
                conversation_id=conv_id,
                workspace_id=ws_id,
                business_category=IntentCategory.COMMERCIAL,
                business_domain=BusinessDomain.SAAS,
                business_process="CANCEL_SUBSCRIPTION",
                taxonomy_path="commercial.churn",
                confidence=0.85,
                classification_method=ClassificationMethod.RULE_BASED,
                supporting_evidence=IntentEvidence(source_message_ids=["msg_4"]),
            ),
        ],
        metadata=ClassificationMetadata(
            conversation_id=conv_id,
            workspace_id=ws_id,
            total_classified_intents=3,
        ),
        diagnostics=ClassificationDiagnostics(
            is_valid=True,
        ),
        provenance=ClassificationProvenance(),
    )

    # 3. Mock Evolution Result
    evolution_result = IntentEvolutionResult(
        entity_id="cust_123",
        current_conversation_id=conv_id,
        workspace_id=ws_id,
        intent_histories=[
            IntentHistory(
                intent_id=intent_id_demo,
                entity_id="cust_123",
                canonical_intent_name="SCHEDULE_DEMO",
                current_state=IntentLifecycleState.ACTIVE,
                timeline=IntentTimeline(
                    intent_id=intent_id_demo,
                    entity_id="cust_123",
                    intent_name="SCHEDULE_DEMO",
                    taxonomy_path="commercial.demo",
                    first_detected_at=now,
                    last_observed_at=now,
                ),
            ),
            IntentHistory(
                intent_id=intent_id_price,
                entity_id="cust_123",
                canonical_intent_name="PRICING_INQUIRY",
                current_state=IntentLifecycleState.ACTIVE,
                timeline=IntentTimeline(
                    intent_id=intent_id_price,
                    entity_id="cust_123",
                    intent_name="PRICING_INQUIRY",
                    taxonomy_path="commercial.pricing",
                    first_detected_at=now,
                    last_observed_at=now,
                ),
            ),
            IntentHistory(
                intent_id=intent_id_cancel,
                entity_id="cust_123",
                canonical_intent_name="CANCEL_SUBSCRIPTION",
                current_state=IntentLifecycleState.NEW,
                timeline=IntentTimeline(
                    intent_id=intent_id_cancel,
                    entity_id="cust_123",
                    intent_name="CANCEL_SUBSCRIPTION",
                    taxonomy_path="commercial.churn",
                    first_detected_at=now,
                    last_observed_at=now,
                ),
            ),
        ],
    )

    repository = ResolutionRepository()
    engine = MultiIntentResolutionEngine(repository=repository)

    result = engine.resolve(
        conversation_id=conv_id,
        entity_id="cust_123",
        workspace_id=ws_id,
        detection_result=detection_result,
        classification_result=classification_result,
        evolution_result=evolution_result,
    )

    assert result is not None
    assert result.conversation_id == conv_id
    assert result.entity_id == "cust_123"
    assert result.workspace_id == ws_id

    # Verify Graph Snapshot (User Directive 7)
    assert result.snapshot.node_count == 3
    assert result.snapshot.graph_version == "1.0.0"
    assert result.snapshot.graph_snapshot_id is not None

    # Verify Relationships detected (Complementary Demo + Pricing)
    assert len(result.resolution_graph.edges) >= 1
    edge_types = [e.relationship_type.value for e in result.resolution_graph.edges]
    assert "COMPLEMENTARY" in edge_types

    # Verify Conflicts detected (Mutually Exclusive Demo/Price vs Cancel)
    assert len(result.resolution_graph.conflicts) >= 1
    conflict_types = [c.conflict_type.value for c in result.resolution_graph.conflicts]
    assert "MUTUALLY_EXCLUSIVE" in conflict_types

    # Verify Dominance Strategy elected dominant intent (User Directive 3)
    assert len(result.dominant_intents) >= 1
    for d in result.dominant_intents:
        assert d.dominance_score >= 0.0
        assert d.primary_factor is not None
        assert len(d.rationale) > 0

    # Verify Provenance (User Directive 4)
    assert result.provenance.resolution_version == "1.0.0"
    assert result.provenance.graph_version == "1.0.0"
    assert result.provenance.rule_pack_version == "1.0.0"
    assert result.provenance.pipeline_version == "2.3.4"
    assert result.provenance.engine_version == "1.0.0"

    # Verify Diagnostics
    assert result.diagnostics.is_valid is True
    assert len(result.diagnostics.stages_executed) == 9

    # Verify Persistence
    persisted = repository.get_by_id(result.resolution_id)
    assert persisted is not None
    assert persisted.resolution_id == result.resolution_id
