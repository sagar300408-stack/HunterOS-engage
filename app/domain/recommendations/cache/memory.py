from __future__ import annotations
import threading
from typing import Dict, Optional, Any
from .interface import IRecommendationCache

class InMemoryRecommendationCache(IRecommendationCache):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Dict[str, Any] = {}

    def get(self, recommendation_id: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(recommendation_id)

    def set(self, recommendation: Any) -> None:
        with self._lock:
            self._cache[recommendation.id] = recommendation

    def delete(self, recommendation_id: str) -> None:
        with self._lock:
            if recommendation_id in self._cache:
                del self._cache[recommendation_id]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
