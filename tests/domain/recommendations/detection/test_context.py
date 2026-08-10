import pytest
import uuid
from datetime import datetime
from app.domain.recommendations.detection.context import RecommendationIntelligenceContextProvider, MemoryContextAdapter, ConversationContextAdapter, IntentContextAdapter, JourneyContextAdapter
from app.domain.recommendations.models import RecommendationTarget

class MockMemory(MemoryContextAdapter):
    def get_memory_context(self, w_id, target): return {"memory_key": "val"}

class MockConv(ConversationContextAdapter):
    def get_conversation_context(self, w_id, target): return {"conv_key": "val"}

class MockIntent(IntentContextAdapter):
    def get_intent_context(self, w_id, target): return {"intent_key": "val"}

class MockJourney(JourneyContextAdapter):
    def get_journey_context(self, w_id, target): return {"journey_key": "val"}

def test_context_provider():
    provider = RecommendationIntelligenceContextProvider(
        MockMemory(), MockConv(), MockIntent(), MockJourney()
    )
    w_id = uuid.uuid4()
    target = RecommendationTarget(target_id="1", target_type="customer")
    context = provider.get_full_context(w_id, target)
    
    assert context["memory"]["memory_key"] == "val"
    assert context["conversation"]["conv_key"] == "val"
    assert context["intent"]["intent_key"] == "val"
    assert context["journey"]["journey_key"] == "val"
