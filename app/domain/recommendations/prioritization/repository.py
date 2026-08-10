from typing import List, Optional
from .models import RecommendationPrioritizationResult

class InMemoryRecommendationPrioritizationRepository:
    def __init__(self):
        self._store = {}
        
    def save(self, result: RecommendationPrioritizationResult) -> None:
        self._store[result.result_id] = result
        
    def get(self, result_id: str) -> Optional[RecommendationPrioritizationResult]:
        return self._store.get(result_id)
        
    def query_by_workspace(self, workspace_id: str) -> List[RecommendationPrioritizationResult]:
        return [res for res in self._store.values() if res.workspace_id == workspace_id]
