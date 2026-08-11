from typing import Dict, Optional, List
from .models import RecommendationIntegrationArtifact
from .cache import IRecommendationContextCache

class InMemoryRecommendationContextRepository(IRecommendationContextCache):
    def __init__(self):
        self._store: Dict[str, RecommendationIntegrationArtifact] = {}
        
    def get(self, artifact_id: str) -> Optional[RecommendationIntegrationArtifact]:
        return self._store.get(artifact_id)
        
    def set(self, artifact: RecommendationIntegrationArtifact) -> None:
        self._store[artifact.artifact_id] = artifact
        
    def invalidate(self, artifact_id: str) -> None:
        if artifact_id in self._store:
            del self._store[artifact_id]
            
    def get_all(self) -> List[RecommendationIntegrationArtifact]:
        return list(self._store.values())
