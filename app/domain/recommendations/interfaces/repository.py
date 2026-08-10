from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

class AbstractRecommendationReadRepository(ABC):
    @abstractmethod
    def get_by_id(self, recommendation_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def list_by_workspace(
        self, 
        workspace_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        pass

    @abstractmethod
    def list_by_target(
        self, 
        target_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        pass

    @abstractmethod
    def filter_by_status(
        self, 
        status: str, 
        workspace_id: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        pass

    @abstractmethod
    def filter_by_type(
        self, 
        rec_type: str, 
        workspace_id: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Any]:
        pass

class AbstractRecommendationWriteRepository(ABC):
    @abstractmethod
    def save(self, recommendation: Any) -> None:
        pass

    @abstractmethod
    def delete(self, recommendation_id: str) -> None:
        pass
