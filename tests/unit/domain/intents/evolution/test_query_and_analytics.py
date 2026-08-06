"""
Unit tests for CQRS IntentEvolutionQuery and descriptive analytics.
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
from app.domain.intents.evolution.query import IntentEvolutionQuery
from app.domain.intents.evolution.repository import IntentEvolutionRepository
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionResult,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)


def test_query_and_descriptive_analytics():
    repo = IntentEvolutionRepository()
    engine = IntentEvolutionEngine(repository=repo)
    query = IntentEvolutionQuery(repository=repo)

    entity_id = "cust-analytics-1"
    intent_id = uuid.uuid4()

    det = DetectedIntent(
        intent_id=intent_id,
        conversation_id="c1",
        intent_type=IntentType.PRICING_INQUIRY,
        title="PricingInquiry",
        taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
        taxonomy_path="commercial/pricing_inquiry",
        confidence=0.90,
        business_importance=BusinessImportance.COMMERCIAL,
        detected_at=datetime.now(timezone.utc),
        supporting_evidence=IntentEvidence(source_message_ids=["msg-1"]),
    )
    res = engine.evolve(
        entity_id=entity_id,
        current_conversation_id="c1",
        entity_type=EntityType.CUSTOMER,
        detection_result=IntentDetectionResult(conversation_id="c1", intents=[det]),
        persist=True,
    )

    # 1. Query history & timeline
    history = query.get_history(intent_id)
    assert history is not None
    assert "pricing" in history.canonical_intent_name.lower()

    timeline = query.get_timeline(intent_id)
    assert timeline is not None
    assert timeline.observation_frequency == 1

    # 2. Query current state
    curr_state = query.get_current_intent_state(intent_id)
    assert curr_state is not None
    assert curr_state["current_lifecycle_state"] == "NEW"

    # 3. Query events with filter
    events = query.get_events(entity_id=entity_id, event_type=IntentEvolutionEventType.INTENT_CREATED)
    assert len(events) == 1

    # 4. Analytics
    analytics = query.get_analytics(entity_id=entity_id, entity_type=EntityType.CUSTOMER)
    assert analytics["entity_id"] == entity_id
    assert analytics["total_evolutions"] >= 1
    assert "NEW" in analytics["state_distribution"]
    assert analytics["evolution_frequency"] >= 1.0
