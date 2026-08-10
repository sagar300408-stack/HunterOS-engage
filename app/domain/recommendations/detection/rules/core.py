from typing import List, Any
from .base import AbstractRecommendationDetectionRule
from app.domain.recommendations.models import RecommendationCandidate, RecommendationTrigger, EvidenceReference

class CoreFollowUpRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "core_follow_up"
    @property
    def rule_name(self) -> str: return "Core Follow-Up Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["FOLLOW_UP"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        if context.get_evidence("requires_follow_up"):
            candidate = RecommendationCandidate(
                recommendation_type="FOLLOW_UP",
                triggers=[RecommendationTrigger(type="SYSTEM_EVENT", reason="Follow up required")],
                evidence=[EvidenceReference(source="context", detail="requires_follow_up=True")]
            )
            candidates.append(candidate)
        return candidates

class CoreContactCustomerRule(AbstractRecommendationDetectionRule):
    @property
    def rule_id(self) -> str: return "core_contact_customer"
    @property
    def rule_name(self) -> str: return "Core Contact Customer Rule"
    @property
    def rule_version(self) -> str: return "1.0.0"
    @property
    def supported_recommendation_types(self) -> List[str]: return ["CONTACT_CUSTOMER"]

    def evaluate(self, context: Any) -> List[Any]:
        candidates = []
        if context.get_evidence("customer_requested_contact"):
            candidate = RecommendationCandidate(
                recommendation_type="CONTACT_CUSTOMER",
                triggers=[RecommendationTrigger(type="USER_REQUEST", reason="Customer explicitly requested contact")],
                evidence=[EvidenceReference(source="conversation", detail="Customer said 'contact me'")]
            )
            candidates.append(candidate)
        return candidates

# Other core rules (Meeting, Site Visit, Document, Information, Pricing, Financing, 
# Property Alternative, Product Alternative, Resolve Request, Escalation, Review Customer)
# would be implemented similarly here, all relying on explicit evidence and no prediction.
