from __future__ import annotations
import threading
from typing import Dict, List, Optional, Any

from .interfaces.repository import AbstractRecommendationReadRepository, AbstractRecommendationWriteRepository

class InMemoryRecommendationRepository(AbstractRecommendationReadRepository, AbstractRecommendationWriteRepository):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._recommendations: Dict[str, Any] = {}

    def get_by_id(self, recommendation_id: str) -> Optional[Any]:
        with self._lock:
            return self._recommendations.get(recommendation_id)

    def list_by_workspace(
        self, 
        workspace_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        with self._lock:
            recs = [r for r in self._recommendations.values() if getattr(r, "workspace_id", None) == workspace_id]
            return recs[offset : offset + limit]

    def list_by_target(
        self, 
        target_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        with self._lock:
            recs = [r for r in self._recommendations.values() if getattr(r, "target_id", None) == target_id]
            return recs[offset : offset + limit]

    def filter_by_status(
        self, 
        status: str, 
        workspace_id: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        with self._lock:
            recs = [r for r in self._recommendations.values() if getattr(r, "status", None) == status]
            if workspace_id is not None:
                recs = [r for r in recs if getattr(r, "workspace_id", None) == workspace_id]
            return recs[offset : offset + limit]

    def filter_by_type(
        self, 
        rec_type: str, 
        workspace_id: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        with self._lock:
            recs = [r for r in self._recommendations.values() if getattr(r, "type", None) == rec_type]
            if workspace_id is not None:
                recs = [r for r in recs if getattr(r, "workspace_id", None) == workspace_id]
            return recs[offset : offset + limit]

    def save(self, recommendation: Any) -> None:
        with self._lock:
            self._recommendations[recommendation.id] = recommendation

    def delete(self, recommendation_id: str) -> None:
        with self._lock:
            if recommendation_id in self._recommendations:
                del self._recommendations[recommendation_id]
