from typing import List, Any
from .base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class JourneyStateRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "journey_state"
    @property
    def rule_name(self) -> str: return "Journey State Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["DISCUSS_FINANCING"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        journey_state = context.get_journey_state()
        
        if journey_state == "NEGOTIATION" and context.get_evidence("finance_document_submitted"):
            candidates.append(
                RecommendationCandidate(
                    recommendation_type="DISCUSS_FINANCING",
                    triggers=[RecommendationTrigger(type="JOURNEY_STATE", reason="Negotiation phase with finance evidence")],
                    evidence=[
                        EvidenceReference(source="journey", detail="State: NEGOTIATION"),
                        EvidenceReference(source="documents", detail="Finance document submitted")
                    ]
                )
            )
        return candidates
