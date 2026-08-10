from __future__ import annotations
from typing import Optional, Any
from .interface import IRecommendationCache

class NullRecommendationCache(IRecommendationCache):
    def get(self, recommendation_id: str) -> Optional[Any]:
        return None

    def set(self, recommendation: Any) -> None:
        pass

    def delete(self, recommendation_id: str) -> None:
        pass

    def clear(self) -> None:
        pass
