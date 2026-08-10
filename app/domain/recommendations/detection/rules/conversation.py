from typing import List, Any
from .base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class ConversationMentionRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "conversation_mention"
    @property
    def rule_name(self) -> str: return "Conversation Mention Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["SEND_DOCUMENT", "SCHEDULE_MEETING"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        mentions = context.get_conversation_mentions()
        
        for mention in mentions:
            if mention.type == "DOCUMENT_REQUEST":
                candidates.append(
                    RecommendationCandidate(
                        recommendation_type="SEND_DOCUMENT",
                        triggers=[RecommendationTrigger(type="CONVERSATION", reason="Explicit mention of document request")],
                        evidence=[EvidenceReference(source="transcript", detail=f"Mentioned at {mention.timestamp}")]
                    )
                )
        return candidates
