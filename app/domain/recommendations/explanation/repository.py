from typing import Dict, Optional, List
from .models import RecommendationExplanation

class InMemoryRecommendationExplanationRepository:
    def __init__(self):
        self._store: Dict[str, RecommendationExplanation] = {}

    def save(self, explanation: RecommendationExplanation) -> None:
        self._store[explanation.explanation_id] = explanation

    def get_by_id(self, explanation_id: str) -> Optional[RecommendationExplanation]:
        return self._store.get(explanation_id)

    def get_by_recommendation_id(self, recommendation_id: str) -> List[RecommendationExplanation]:
        return [ex for ex in self._store.values() if ex.recommendation_id == recommendation_id]

    def delete(self, explanation_id: str) -> None:
        if explanation_id in self._store:
            del self._store[explanation_id]
