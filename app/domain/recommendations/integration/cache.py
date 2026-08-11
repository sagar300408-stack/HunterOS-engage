from abc import ABC, abstractmethod
from typing import Optional
from .models import RecommendationIntegrationArtifact

class IRecommendationContextCache(ABC):
    @abstractmethod
    def get(self, artifact_id: str) -> Optional[RecommendationIntegrationArtifact]:
        pass
        
    @abstractmethod
    def set(self, artifact: RecommendationIntegrationArtifact) -> None:
        pass
        
    @abstractmethod
    def invalidate(self, artifact_id: str) -> None:
        pass
