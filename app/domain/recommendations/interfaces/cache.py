from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

class IRecommendationCache(ABC):
    @abstractmethod
    def get(self, recommendation_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, recommendation: Any) -> None:
        pass

    @abstractmethod
    def delete(self, recommendation_id: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
