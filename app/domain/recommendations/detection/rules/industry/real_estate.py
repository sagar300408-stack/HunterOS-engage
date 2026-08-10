from typing import List, Any
from ..base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class RealEstateRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "real_estate_brochure"
    @property
    def rule_name(self) -> str: return "Real Estate Brochure Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["SEND_DOCUMENT"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        if context.get_evidence("property_inquiry") and context.get_evidence("brochure_request"):
            candidates.append(
                RecommendationCandidate(
                    recommendation_type="SEND_DOCUMENT",
                    triggers=[RecommendationTrigger(type="INDUSTRY_SPECIFIC", reason="Property inquiry + brochure request")],
                    evidence=[
                        EvidenceReference(source="inquiry", detail="Property inquiry exists"),
                        EvidenceReference(source="request", detail="Brochure request exists")
                    ]
                )
            )
        return candidates
