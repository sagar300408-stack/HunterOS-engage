from .base import BaseView
from ..models import RecommendationExplanation

class AuditView(BaseView):
    def render(self, explanation: RecommendationExplanation) -> str:
        return (
            f"Audit View: {explanation.title}\n"
            f"Provenance: {explanation.provenance}\n"
            f"Full Evidence: {explanation.evidence}\n"
            f"Factor Breakdown: {explanation.factor_explanations}"
        )
