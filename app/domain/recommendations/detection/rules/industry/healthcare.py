from typing import List, Any
from ..base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class HealthcareConservativeRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "healthcare_conservative"
    @property
    def rule_name(self) -> str: return "Healthcare Conservative Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["SCHEDULE_MEETING"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        # Highly conservative: only recommend if explicit patient consent and explicit request exist
        if context.get_evidence("patient_consent") and context.get_evidence("consultation_request"):
            candidates.append(
                RecommendationCandidate(
                    recommendation_type="SCHEDULE_MEETING",
                    triggers=[RecommendationTrigger(type="HEALTHCARE_STRICT", reason="Consent and explicit consultation request present")],
                    evidence=[
                        EvidenceReference(source="consent", detail="Patient consent recorded"),
                        EvidenceReference(source="request", detail="Consultation explicitly requested")
                    ]
                )
            )
        return candidates
