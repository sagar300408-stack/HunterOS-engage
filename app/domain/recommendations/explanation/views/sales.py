from .base import BaseView
from ..models import RecommendationExplanation

class SalesView(BaseView):
    def render(self, explanation: RecommendationExplanation) -> str:
        return f"Sales View: {explanation.title}\nCommercial Focus: {explanation.priority_reason}\nKey Evidence: {[e.description for e in explanation.evidence]}"
