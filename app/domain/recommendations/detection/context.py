from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

from app.domain.recommendations.models import RecommendationTarget
from .models import RecommendationDetectionResult

class MemoryContextAdapter:
    """ACL Interface for memory context."""
    def get_memory_context(self, workspace_id: UUID, target: RecommendationTarget) -> Dict[str, Any]:
        raise NotImplementedError

class ConversationContextAdapter:
    """ACL Interface for conversation context."""
    def get_conversation_context(self, workspace_id: UUID, target: RecommendationTarget) -> Dict[str, Any]:
        raise NotImplementedError

class IntentContextAdapter:
    """ACL Interface for intent context."""
    def get_intent_context(self, workspace_id: UUID, target: RecommendationTarget) -> Dict[str, Any]:
        raise NotImplementedError

class JourneyContextAdapter:
    """ACL Interface for journey context."""
    def get_journey_context(self, workspace_id: UUID, target: RecommendationTarget) -> Dict[str, Any]:
        raise NotImplementedError

class RecommendationIntelligenceContextProvider:
    """Combines various context adapters to build a comprehensive context."""
    def __init__(
        self,
        memory_adapter: MemoryContextAdapter,
        conversation_adapter: ConversationContextAdapter,
        intent_adapter: IntentContextAdapter,
        journey_adapter: JourneyContextAdapter,
    ):
        self.memory_adapter = memory_adapter
        self.conversation_adapter = conversation_adapter
        self.intent_adapter = intent_adapter
        self.journey_adapter = journey_adapter

    def get_full_context(self, workspace_id: UUID, target: RecommendationTarget) -> Dict[str, Any]:
        return {
            "memory": self.memory_adapter.get_memory_context(workspace_id, target),
            "conversation": self.conversation_adapter.get_conversation_context(workspace_id, target),
            "intent": self.intent_adapter.get_intent_context(workspace_id, target),
            "journey": self.journey_adapter.get_journey_context(workspace_id, target),
        }

@dataclass(frozen=True)
class RecommendationDetectionContext:
    workspace_id: UUID
    target: RecommendationTarget
    memory_context: Dict[str, Any]
    conversation_context: Dict[str, Any]
    intent_context: Dict[str, Any]
    journey_context: Dict[str, Any]
    existing_recommendations: List[Any]  # Upstream existing recommendations
    current_time: datetime
    execution_metadata: Dict[str, Any]
    correlation_id: str
