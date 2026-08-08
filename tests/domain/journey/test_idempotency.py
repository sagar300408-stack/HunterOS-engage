from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyType,
)
from app.domain.journey.registry import register_core_definitions
from app.domain.journey.repository import InMemoryJourneyRepository


def test_repeated_progression_with_same_evidence_does_not_create_duplicate_transitions():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    engine = JourneyIntelligenceEngine(read_repository=repo, write_repository=repo)

    state = engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)

    evidence = [
        JourneyEvidence(
            evidence_id=uuid.uuid4(),
            evidence_type=EvidenceType.INTENT,
            source_module="system",
            timestamp=datetime.now(timezone.utc),
            description="inquiry",
            confidence=0.9,
        )
    ]

    context = JourneyProgressionContext(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.85}]},
        conversation_context={},
        memory_context={},
        evidence=evidence,
        evaluated_at=datetime.now(timezone.utc),
    )

    result1 = engine.progress(context)
    assert result1.transition_occurred is True

    # Repeat progression with the new state but same intent
    context2 = JourneyProgressionContext(
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        journey_state=result1.new_state,
        journey_definition=engine.get_journey_definition(state.journey_definition_id),
        intent_context={"detected_intents": [{"intent_type": "PROPERTY_INQUIRY", "confidence": 0.85}]},
        conversation_context={},
        memory_context={},
        evidence=evidence,
        evaluated_at=datetime.now(timezone.utc),
    )
    result2 = engine.progress(context2)

    # Should not transition again from INTERESTED to INTERESTED
    assert result2.transition_occurred is False


def test_progression_fingerprint_is_deterministic():
    repo = InMemoryJourneyRepository()
    register_core_definitions()
    engine = JourneyIntelligenceEngine(read_repository=repo, write_repository=repo)
    state = engine.create_journey("ws1", "CUSTOMER", "lead1", JourneyType.SALES)
    fp1 = state.compute_progression_fingerprint(["e1", "e2"], "1.0.0")
    fp2 = state.compute_progression_fingerprint(["e1", "e2"], "1.0.0")
    assert fp1 == fp2
