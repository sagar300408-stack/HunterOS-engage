from .base import BaseView
from ..models import RecommendationExplanation

class OperationsView(BaseView):
    def render(self, explanation: RecommendationExplanation) -> str:
        return f"Operations View: {explanation.title}\nBlockers/Limitations: {', '.join(explanation.limitations)}"
