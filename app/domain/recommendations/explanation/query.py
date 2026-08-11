from typing import List, Optional
from .repository import InMemoryRecommendationExplanationRepository
from .models import RecommendationExplanation

class RecommendationExplanationQueryEngine:
    def __init__(self, repository: InMemoryRecommendationExplanationRepository):
        self.repository = repository

    def get_explanation(self, explanation_id: str) -> Optional[RecommendationExplanation]:
        return self.repository.get_by_id(explanation_id)

    def list_explanations_for_recommendation(self, recommendation_id: str) -> List[RecommendationExplanation]:
        return self.repository.get_by_recommendation_id(recommendation_id)
