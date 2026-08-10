from __future__ import annotations
from typing import List, Optional, Any

from .interfaces.repository import AbstractRecommendationReadRepository

class RecommendationQueryEngine:
    def __init__(self, repository: AbstractRecommendationReadRepository) -> None:
        self._repository = repository

    def get_recommendation(self, recommendation_id: str) -> Optional[Any]:
        return self._repository.get_by_id(recommendation_id)

    def list_recommendations(self, workspace_id: str, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.list_by_workspace(workspace_id, limit, offset)
        
    def get_by_customer(self, customer_id: str, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.list_by_target(customer_id, limit, offset)

    def get_by_workspace(self, workspace_id: str, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.list_by_workspace(workspace_id, limit, offset)

    def get_by_status(self, status: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.filter_by_status(status, workspace_id, limit, offset)

    def get_by_type(self, rec_type: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.filter_by_type(rec_type, workspace_id, limit, offset)

    def get_active(self, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Any]:
        return self._repository.filter_by_status("ACTIVE", workspace_id, limit, offset)

    def get_recent(self, workspace_id: str, limit: int = 10, offset: int = 0) -> List[Any]:
        # Typically would sort by created_at, but we just list them here.
        recs = self._repository.list_by_workspace(workspace_id, limit=limit, offset=offset)
        recs_sorted = sorted(recs, key=lambda r: getattr(r, "created_at", 0), reverse=True)
        return recs_sorted

    def count_by_status(self, status: str, workspace_id: Optional[str] = None) -> int:
        # A more optimal implementation would push this to the DB, but this works for abstract interface.
        # Alternatively, assume the repository has a count method. For now, fetch all or a large number.
        recs = self._repository.filter_by_status(status, workspace_id, limit=10000, offset=0)
        return len(recs)

    def count_by_type(self, rec_type: str, workspace_id: Optional[str] = None) -> int:
        recs = self._repository.filter_by_type(rec_type, workspace_id, limit=10000, offset=0)
        return len(recs)
