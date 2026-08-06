"""
Unit tests for the 8-stage IntentEvolutionPipeline and IntentEvolutionEngine.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.evolution.engine import IntentEvolutionEngine
from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEventType,
    IntentLifecycleState,
)
from app.domain.intents.evolution.repository import IntentEvolutionRepository
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionResult,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)


def _make_detection_result(intent_id: uuid.UUID, title: str, confidence: float, conv_id: str) -> IntentDetectionResult:
    det = DetectedIntent(
        intent_id=intent_id,
        conversation_id=conv_id,
        intent_type=IntentType.PRICING_INQUIRY,
        taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
        taxonomy_path="commercial/pricing_inquiry",
        title=title,
        confidence=confidence,
        business_importance=BusinessImportance.COMMERCIAL,
        detected_at=datetime.now(timezone.utc),
        supporting_evidence=IntentEvidence(source_message_ids=["msg-1"]),
    )
    return IntentDetectionResult(
        conversation_id=conv_id,
        intents=[det],
    )


def test_multi_conversation_evolution_lifecycle():
    repo = IntentEvolutionRepository()
    engine = IntentEvolutionEngine(repository=repo)

    entity_id = "cust-multi-1"
    intent_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    # --- Conversation 1: Initial Discovery ---
    det1 = _make_detection_result(intent_id, "DemoRequest", 0.70, "conv-001")
    res1 = engine.evolve(
        entity_id=entity_id,
        current_conversation_id="conv-001",
        entity_type=EntityType.CUSTOMER,
        workspace_id=workspace_id,
        detection_result=det1,
        persist=True,
    )

    assert len(res1.timelines) == 1
    t1 = res1.timelines[0]
    assert t1.current_lifecycle_state == IntentLifecycleState.NEW
    assert t1.observation_frequency == 1
    assert len(res1.event_stream.events) >= 1
    assert res1.diagnostics.is_valid is True
    assert len(res1.diagnostics.stages_executed) == 8

    # --- Conversation 2: Follow-up & Confidence Increase ---
    det2 = _make_detection_result(intent_id, "DemoRequest", 0.92, "conv-002")
    res2 = engine.evolve(
        entity_id=entity_id,
        current_conversation_id="conv-002",
        entity_type=EntityType.CUSTOMER,
        workspace_id=workspace_id,
        detection_result=det2,
        persist=True,
    )

    assert len(res2.timelines) == 1
    t2 = res2.timelines[0]
    assert t2.observation_frequency == 2
    assert "conv-001" in t2.source_conversations
    assert "conv-002" in t2.source_conversations
    assert t2.current_confidence == 0.92

    # Check that events from both conversations exist in immutable stream
    stream = repo.get_event_stream(entity_id=entity_id, entity_type=EntityType.CUSTOMER, workspace_id=workspace_id)
    assert stream is not None
    assert stream.version >= 2
    assert len(stream.events) >= 2


def test_empty_or_no_detections_pipeline():
    repo = IntentEvolutionRepository()
    engine = IntentEvolutionEngine(repository=repo)

    res = engine.evolve(
        entity_id="cust-empty",
        current_conversation_id="conv-empty",
        entity_type=EntityType.CUSTOMER,
        persist=False,
    )

    assert len(res.timelines) == 0
    assert len(res.intent_histories) == 0
    assert res.metadata.total_active_intents == 0
    assert res.diagnostics.is_valid is True
