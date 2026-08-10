from __future__ import annotations

import abc
from typing import Any, Dict, Optional

class IJourneyContextCache(abc.ABC):
    @abc.abstractmethod
    def get(self, workspace_id: str, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        pass

    @abc.abstractmethod
    def set(self, workspace_id: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Sets a value in the cache."""
        pass

    @abc.abstractmethod
    def invalidate(self, workspace_id: str, key: str) -> None:
        """Invalidates a specific key in the cache."""
        pass

    @abc.abstractmethod
    def clear(self, workspace_id: str) -> None:
        """Clears all cached values for a given workspace."""
        pass

class InMemoryJourneyContextCache(IJourneyContextCache):
    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, workspace_id: str, key: str) -> Optional[Any]:
        return self._cache.get(workspace_id, {}).get(key)

    def set(self, workspace_id: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if workspace_id not in self._cache:
            self._cache[workspace_id] = {}
        self._cache[workspace_id][key] = value

    def invalidate(self, workspace_id: str, key: str) -> None:
        if workspace_id in self._cache and key in self._cache[workspace_id]:
            del self._cache[workspace_id][key]

    def clear(self, workspace_id: str) -> None:
        if workspace_id in self._cache:
            self._cache[workspace_id].clear()

class NullJourneyContextCache(IJourneyContextCache):
    def get(self, workspace_id: str, key: str) -> Optional[Any]:
        return None

    def set(self, workspace_id: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        pass

    def invalidate(self, workspace_id: str, key: str) -> None:
        pass

    def clear(self, workspace_id: str) -> None:
        pass
