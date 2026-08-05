"""
HunterOS Engage — Context Cache Interface (Phase 2.1.5)

Defines the abstract caching contract for composed context payloads.
Strictly specifies interface boundaries without coupling to a concrete distributed cache provider.
"""

from __future__ import annotations

import abc
from typing import Optional

from app.domain.memory.intelligence.models import ComposedContext


class AbstractContextCache(abc.ABC):
    """
    Abstract interface for caching composed intelligence contexts.
    """

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[ComposedContext]:
        """Retrieve a cached ComposedContext by cache key."""
        raise NotImplementedError

    @abc.abstractmethod
    async def set(
        self,
        key: str,
        value: ComposedContext,
        ttl_seconds: int = 300,
    ) -> None:
        """Cache a ComposedContext with an optional TTL in seconds."""
        raise NotImplementedError

    @abc.abstractmethod
    async def invalidate(self, key: str) -> None:
        """Invalidate a specific cache key."""
        raise NotImplementedError

    @abc.abstractmethod
    async def has(self, key: str) -> bool:
        """Check if a cache key exists."""
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear all entries in cache."""
        raise NotImplementedError


class NoOpContextCache(AbstractContextCache):
    """
    Default pass-through context cache ensuring zero side effects.
    """

    async def get(self, key: str) -> Optional[ComposedContext]:
        return None

    async def set(self, key: str, value: ComposedContext, ttl_seconds: int = 300) -> None:
        pass

    async def invalidate(self, key: str) -> None:
        pass

    async def has(self, key: str) -> bool:
        return False

    async def clear(self) -> None:
        pass


class InMemoryContextCache(AbstractContextCache):
    """
    In-memory dictionary cache provider suitable for local testing.
    """

    def __init__(self) -> None:
        self._store: dict[str, ComposedContext] = {}

    async def get(self, key: str) -> Optional[ComposedContext]:
        return self._store.get(key)

    async def set(self, key: str, value: ComposedContext, ttl_seconds: int = 300) -> None:
        self._store[key] = value

    async def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    async def has(self, key: str) -> bool:
        return key in self._store

    async def clear(self) -> None:
        self._store.clear()
