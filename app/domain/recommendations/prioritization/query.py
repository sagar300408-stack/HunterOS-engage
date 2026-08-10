from typing import List
from .models import RecommendationPrioritizationResult
from .repository import InMemoryRecommendationPrioritizationRepository

class RecommendationPrioritizationQueryEngine:
    def __init__(self, repository: InMemoryRecommendationPrioritizationRepository):
        self._repository = repository
        
    def get_latest_for_workspace(self, workspace_id: str) -> List[RecommendationPrioritizationResult]:
        # Simple implementation, returning all matches. 
        # In real life this would sort by created_at and return the latest
        results = self._repository.query_by_workspace(workspace_id)
        return sorted(results, key=lambda x: x.created_at, reverse=True)
