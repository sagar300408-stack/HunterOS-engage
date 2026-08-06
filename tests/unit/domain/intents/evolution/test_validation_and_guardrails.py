"""
Unit tests for EvolutionValidator Guardrails (Monotonicity, Matrix, Isolation, Confidence).
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentEvolutionEventType,
    IntentLifecycleState,
    IntentStateTransition,
    IntentTimeline,
    IntentVelocity,
)
from app.domain.intents.evolution.validation import EvolutionValidator


def test_validator_monotonicity():
    validator = EvolutionValidator()
    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 1. Invalid first_detected_at > last_observed_at
    bad_timeline = IntentTimeline(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-1",
        intent_name="Test",
        taxonomy_path="Test/Path",
        first_detected_at=now + timedelta(hours=5),
        last_observed_at=now,
        observation_frequency=1,
        velocity=IntentVelocity.STABLE,
        source_conversations=["c1"],
        current_lifecycle_state=IntentLifecycleState.NEW,
        current_confidence=0.8,
    )
    errors = validator.validate_timeline_consistency(bad_timeline)
    assert any("Temporal monotonicity violation" in e for e in errors)

    # 2. Valid timeline
    good_timeline = IntentTimeline(
        intent_id=intent_id,
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-1",
        intent_name="Test",
        taxonomy_path="Test/Path",
        first_detected_at=now - timedelta(days=1),
        last_observed_at=now,
        observation_frequency=2,
        velocity=IntentVelocity.STABLE,
        source_conversations=["c1", "c2"],
        current_lifecycle_state=IntentLifecycleState.PERSISTING,
        current_confidence=0.85,
    )
    assert len(validator.validate_timeline_consistency(good_timeline)) == 0


def test_validator_transition_matrix():
    validator = EvolutionValidator()
    now = datetime.now(timezone.utc)

    # Legal transition: NEW -> PERSISTING
    legal_t = IntentStateTransition(
        from_state=IntentLifecycleState.NEW,
        to_state=IntentLifecycleState.PERSISTING,
        transition_reason="Second observation",
        transitioned_at=now,
    )
    assert len(validator.validate_transition(legal_t)) == 0

    # Illegal transition: CLOSED -> STRENGTHENING
    illegal_t = IntentStateTransition(
        from_state=IntentLifecycleState.CLOSED,
        to_state=IntentLifecycleState.STRENGTHENING,
        transition_reason="Illegal direct jump",
        transitioned_at=now,
    )
    errors = validator.validate_transition(illegal_t)
    assert len(errors) == 1
    assert "Illegal state transition" in errors[0]


def test_validator_workspace_isolation():
    validator = EvolutionValidator()
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    event = IntentEvolutionEvent(
        intent_id=uuid.uuid4(),
        entity_type=EntityType.CUSTOMER,
        entity_id="cust-1",
        workspace_id=ws_b,  # Belongs to ws_b
        event_type=IntentEvolutionEventType.INTENT_CREATED,
        current_state=IntentLifecycleState.NEW,
    )

    # Attempt validation against ws_a
    errors = validator.validate_workspace_isolation(ws_a, [event])
    assert len(errors) == 1
    assert "Cross-workspace isolation breach" in errors[0]


def test_validator_confidence_bounds():
    validator = EvolutionValidator()

    assert len(validator.validate_confidence(0.5, "Intent1")) == 0
    assert len(validator.validate_confidence(1.0, "Intent1")) == 0
    assert len(validator.validate_confidence(0.0, "Intent1")) == 0

    err_high = validator.validate_confidence(1.2, "Intent1")
    assert len(err_high) == 1
    assert "out of bounds" in err_high[0]

    err_low = validator.validate_confidence(-0.1, "Intent1")
    assert len(err_low) == 1
    assert "out of bounds" in err_low[0]
