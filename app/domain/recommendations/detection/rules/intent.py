from typing import List, Any
from .base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class IntentMappingRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "intent_mapping"
    @property
    def rule_name(self) -> str: return "Intent Mapping Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["DISCUSS_FINANCING", "PROVIDE_INFORMATION"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        intents = context.get_intents()
        
        for intent in intents:
            if intent.type == "FINANCE_INQUIRY" and context.get_evidence("financing_evidence_exists"):
                candidates.append(
                    RecommendationCandidate(
                        recommendation_type="DISCUSS_FINANCING",
                        triggers=[RecommendationTrigger(type="INTENT", reason="Explicit finance inquiry intent detected")],
                        evidence=[EvidenceReference(source="intent_parser", detail="Intent: FINANCE_INQUIRY")]
                    )
                )
        return candidates
