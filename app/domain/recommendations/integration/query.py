from typing import List, Optional
from .models import RecommendationIntegrationArtifact
from .repository import InMemoryRecommendationContextRepository

class RecommendationIntegrationQueryEngine:
    def __init__(self, repository: InMemoryRecommendationContextRepository):
        self.repository = repository
        
    def get_by_id(self, artifact_id: str) -> Optional[RecommendationIntegrationArtifact]:
        return self.repository.get(artifact_id)
        
    def get_by_identity(self, identity_id: str) -> List[RecommendationIntegrationArtifact]:
        return [
            artifact for artifact in self.repository.get_all()
            if artifact.context.identity_id == identity_id
        ]
