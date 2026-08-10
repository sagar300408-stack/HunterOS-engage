from typing import List, Dict, Any
from dataclasses import dataclass
from .models import RecommendationCandidate

@dataclass(frozen=True)
class RecommendationPrioritizationContext:
    _workspace_id: str
    _candidate_recommendations: List[RecommendationCandidate]
    _configuration: Dict[str, Any]
    _upstream_acl_contexts: List[Any] = None
    
    @property
    def workspace_id(self) -> str:
        return self._workspace_id
        
    @property
    def candidate_recommendations(self) -> List[RecommendationCandidate]:
        return list(self._candidate_recommendations)
        
    @property
    def configuration(self) -> Dict[str, Any]:
        return dict(self._configuration)
        
    @property
    def upstream_acl_contexts(self) -> List[Any]:
        return list(self._upstream_acl_contexts) if self._upstream_acl_contexts else []
