"""
Unit tests for Intent Evolution Domain Models, Enums, and Aggregates.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.evolution.models import (
    EntityType,
    EvolutionDiagnostics,
    EvolutionMetadata,
    EvolutionProvenance,
    IntentEvolutionEvent,
    IntentEvolutionEventStream,
    IntentEvolutionEventType,
    IntentEvolutionResult,
    IntentHistory,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
    IntentTimeline,
    IntentVelocity,
)


def test_evolution_enums():
    assert EntityType.CUSTOMER.value == "CUSTOMER"
    assert EntityType.ORGANIZATION.value == "ORGANIZATION"
    assert EntityType.DEAL.value == "DEAL"

    assert IntentLifecycleState.NEW.value == "NEW"
    assert IntentLifecycleState.PERSISTING.value == "PERSISTING"
    assert IntentLifecycleState.STRENGTHENING.value == "STRENGTHENING"
    assert IntentLifecycleState.WEAKENING.value == "WEAKENING"
    assert IntentLifecycleState.RESOLVED.value == "RESOLVED"
    assert IntentLifecycleState.CLOSED.value == "CLOSED"

    assert IntentEvolutionEventType.INTENT_CREATED.value == "INTENT_CREATED"
    assert IntentEvolutionEventType.INTENT_MERGED.value == "INTENT_MERGED"
    assert IntentEvolutionEventType.INTENT_SPLIT.value == "INTENT_SPLIT"

    assert IntentVelocity.INCREASING.value == "INCREASING"
    assert IntentVelocity.DECREASING.value == "DECREASING"


def test_intent_state_snapshot_and_serialization():
    intent_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    snap = IntentStateSnapshot(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-123",
        conversation_id="conv-1",
        workspace_id=workspace_id,
        intent_type="PricingInquiry",
        category="Sales",
        taxonomy_path="Sales/Pricing/Quote",
        confidence=0.92,
        observed_at=now,
        evidence_message_ids=["msg-1", "msg-2"],
        relationships=[{"target": "PropertyInquiry", "type": "RELATED"}],
        metadata={"source": "test"},
    )

    data = snap.to_dict()
    assert data["intent_id"] == str(intent_id)
    assert data["entity_type"] == "CUSTOMER"
    assert data["entity_id"] == "cust-123"
    assert data["confidence"] == 0.92
    assert len(data["evidence_message_ids"]) == 2
    assert len(data["relationships"]) == 1


def test_intent_evolution_event_stream_immutability():
    intent_id = uuid.uuid4()
    stream = IntentEvolutionEventStream(
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
    )
    assert stream.version == 1
    assert len(stream.events) == 0

    event1 = IntentEvolutionEvent(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        event_type=IntentEvolutionEventType.INTENT_CREATED,
        current_state=IntentLifecycleState.NEW,
    )

    stream2 = stream.append(event1)
    assert stream.version == 1
    assert len(stream.events) == 0  # Original unchanged

    assert stream2.version == 2
    assert len(stream2.events) == 1
    assert stream2.events[0].event_type == IntentEvolutionEventType.INTENT_CREATED


def test_intent_timeline_and_history():
    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    timeline = IntentTimeline(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        intent_name="PricingInquiry",
        taxonomy_path="Sales/Pricing",
        first_detected_at=now,
        last_observed_at=now,
        observation_frequency=1,
        velocity=IntentVelocity.STABLE,
        source_conversations=["conv-1"],
        current_lifecycle_state=IntentLifecycleState.NEW,
        current_confidence=0.95,
    )

    history = IntentHistory(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        canonical_intent_name="PricingInquiry",
        current_state=IntentLifecycleState.NEW,
        timeline=timeline,
        created_at=now,
        updated_at=now,
    )

    h_data = history.to_dict()
    assert h_data["intent_id"] == str(intent_id)
    assert h_data["canonical_intent_name"] == "PricingInquiry"
    assert h_data["current_state"] == "NEW"
    assert h_data["timeline"]["observation_frequency"] == 1


def test_intent_evolution_result_aggregate_root():
    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    timeline = IntentTimeline(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        intent_name="Booking",
        taxonomy_path="Sales/Booking",
        first_detected_at=now,
        last_observed_at=now,
        observation_frequency=2,
        velocity=IntentVelocity.INCREASING,
        source_conversations=["conv-1", "conv-2"],
        current_lifecycle_state=IntentLifecycleState.STRENGTHENING,
        current_confidence=0.98,
    )

    history = IntentHistory(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        canonical_intent_name="Booking",
        current_state=IntentLifecycleState.STRENGTHENING,
        timeline=timeline,
        created_at=now,
        updated_at=now,
    )

    result = IntentEvolutionResult(
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-100",
        current_conversation_id="conv-2",
        intent_histories=[history],
        timelines=[timeline],
        metadata=EvolutionMetadata(
            entity_type=EntityType.CUSTOMER,
            entity_id="cust-100",
            total_active_intents=1,
        ),
        diagnostics=EvolutionDiagnostics(is_valid=True),
        generated_at=now,
    )

    assert result.customer_id == "cust-100"
    assert result.get_history_by_intent(intent_id) == history
    assert result.get_timeline_by_intent(intent_id) == timeline
    assert result.get_history_by_intent(uuid.uuid4()) is None
