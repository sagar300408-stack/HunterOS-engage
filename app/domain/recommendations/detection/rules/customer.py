from typing import List, Any
from .base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class CustomerMemoryRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "customer_memory"
    @property
    def rule_name(self) -> str: return "Customer Memory Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["SEND_DOCUMENT"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        
        # Memory should only SUPPORT a rule, not invent purely from memory.
        # Example: if there's an explicit request for document AND memory preferred channel is email
        if context.get_evidence("document_requested") and context.get_memory("preferred_channel") == "email":
            candidates.append(
                RecommendationCandidate(
                    recommendation_type="SEND_DOCUMENT_VIA_EMAIL",
                    triggers=[RecommendationTrigger(type="MEMORY_SUPPORTED", reason="Requested document, preferred channel is email")],
                    evidence=[
                        EvidenceReference(source="context", detail="Document requested explicit evidence"),
                        EvidenceReference(source="memory", detail="Preferred channel: email")
                    ]
                )
            )
        return candidates
