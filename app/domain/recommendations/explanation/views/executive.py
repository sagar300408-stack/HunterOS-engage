from .base import BaseView
from ..models import RecommendationExplanation

class ExecutiveView(BaseView):
    def render(self, explanation: RecommendationExplanation) -> str:
        return f"Executive Summary: {explanation.title}\nSummary: {explanation.summary}\nTop Reason: {explanation.recommendation_reason}"
