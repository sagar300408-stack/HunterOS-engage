"""
HunterOS Engage — Memory Query Cache Layer (Implementation-Agnostic)

Provides an abstract cache interface and a default thread-safe in-memory cache
with TTL support, tag-based invalidation, and workspace/customer scoping.
Designed for drop-in replacement with distributed Redis providers in future phases.
"""

import abc
import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set
from uuid import UUID


class AbstractMemoryQueryCacheProvider(abc.ABC):
    """
    Abstract interface for Query Cache Providers.
    Follows CQRS principles: Query caches are read by query engines
    and invalidated upon write-side domain events.
    """

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached query result."""
        raise NotImplementedError

    @abc.abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,
        customer_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Cache a query result with TTL and invalidation tags."""
        raise NotImplementedError

    @abc.abstractmethod
    async def invalidate_customer(self, customer_id: UUID) -> int:
        """Invalidate all cached queries related to a specific customer."""
        raise NotImplementedError

    @abc.abstractmethod
    async def invalidate_workspace(self, workspace_id: UUID) -> int:
        """Invalidate all cached queries related to a specific workspace."""
        raise NotImplementedError

    @abc.abstractmethod
    async def invalidate_all(self) -> int:
        """Clear all cached query results."""
        raise NotImplementedError

    @abc.abstractmethod
    def generate_cache_key(self, prefix: str, query_params: Dict[str, Any]) -> str:
        """Generate a deterministic SHA-256 hash cache key from query params."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Return cache hit, miss, and count metrics."""
        raise NotImplementedError


class _CacheEntry:
    """Internal cache storage wrapper."""

    __slots__ = ("value", "expires_at", "customer_id", "workspace_id", "tags")

    def __init__(
        self,
        value: Any,
        expires_at: float,
        customer_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        self.value = value
        self.expires_at = expires_at
        self.customer_id = str(customer_id) if customer_id else None
        self.workspace_id = str(workspace_id) if workspace_id else None
        self.tags: Set[str] = set(tags or [])


class DefaultMemoryQueryCacheProvider(AbstractMemoryQueryCacheProvider):
    """
    Default in-memory query cache implementation.
    Thread-safe and async-safe with automatic TTL expiration,
    customer/workspace tracking, and operational metric recording.
    """

    def __init__(self, default_ttl_seconds: int = 300, max_entries: int = 5000) -> None:
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries
        self._store: Dict[str, _CacheEntry] = {}
        self._customer_index: Dict[str, Set[str]] = {}
        self._workspace_index: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

        # Operational metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def generate_cache_key(self, prefix: str, query_params: Dict[str, Any]) -> str:
        """Generate deterministic cache key from parameters."""
        try:
            serialized = json.dumps(query_params, sort_keys=True, default=str)
        except Exception:
            serialized = str(sorted(query_params.items()))
        param_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"mem_q:{prefix}:{param_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if not expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            now = time.time()
            if now > entry.expires_at:
                self._misses += 1
                self._delete_entry(key, entry)
                return None

            self._hits += 1
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        customer_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Store query result in cache with tracking indexes."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.time() + ttl

        async with self._lock:
            # Enforce max entries limit (evict oldest if full)
            if len(self._store) >= self._max_entries and key not in self._store:
                self._evict_expired_or_oldest()

            entry = _CacheEntry(
                value=value,
                expires_at=expires_at,
                customer_id=customer_id,
                workspace_id=workspace_id,
                tags=tags,
            )
            self._store[key] = entry

            if entry.customer_id:
                self._customer_index.setdefault(entry.customer_id, set()).add(key)
            if entry.workspace_id:
                self._workspace_index.setdefault(entry.workspace_id, set()).add(key)

    async def invalidate_customer(self, customer_id: UUID) -> int:
        """Invalidate all keys associated with a customer."""
        cid_str = str(customer_id)
        count = 0
        async with self._lock:
            keys = self._customer_index.pop(cid_str, set())
            for key in keys:
                entry = self._store.pop(key, None)
                if entry:
                    count += 1
                    if entry.workspace_id and entry.workspace_id in self._workspace_index:
                        self._workspace_index[entry.workspace_id].discard(key)
        return count

    async def invalidate_workspace(self, workspace_id: UUID) -> int:
        """Invalidate all keys associated with a workspace."""
        wid_str = str(workspace_id)
        count = 0
        async with self._lock:
            keys = self._workspace_index.pop(wid_str, set())
            for key in keys:
                entry = self._store.pop(key, None)
                if entry:
                    count += 1
                    if entry.customer_id and entry.customer_id in self._customer_index:
                        self._customer_index[entry.customer_id].discard(key)
        return count

    async def invalidate_all(self) -> int:
        """Clear the entire cache."""
        async with self._lock:
            count = len(self._store)
            self._store.clear()
            self._customer_index.clear()
            self._workspace_index.clear()
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Return cache health and hit-ratio metrics."""
        total_requests = self._hits + self._misses
        hit_ratio = (self._hits / total_requests) if total_requests > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_ratio": round(hit_ratio, 4),
            "current_size": len(self._store),
            "max_size": self._max_entries,
            "evictions": self._evictions,
        }

    def _delete_entry(self, key: str, entry: _CacheEntry) -> None:
        self._store.pop(key, None)
        if entry.customer_id and entry.customer_id in self._customer_index:
            self._customer_index[entry.customer_id].discard(key)
        if entry.workspace_id and entry.workspace_id in self._workspace_index:
            self._workspace_index[entry.workspace_id].discard(key)

    def _evict_expired_or_oldest(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired_keys:
            self._delete_entry(k, self._store[k])
            self._evictions += 1

        if len(self._store) >= self._max_entries:
            # Evict first available item (FIFO)
            first_key = next(iter(self._store))
            self._delete_entry(first_key, self._store[first_key])
            self._evictions += 1


class NullQueryCacheProvider(AbstractMemoryQueryCacheProvider):
    """Pass-through no-op cache provider when caching is disabled."""

    def generate_cache_key(self, prefix: str, query_params: Dict[str, Any]) -> str:
        return f"null:{prefix}"

    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,
        customer_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        pass

    async def invalidate_customer(self, customer_id: UUID) -> int:
        return 0

    async def invalidate_workspace(self, workspace_id: UUID) -> int:
        return 0

    async def invalidate_all(self) -> int:
        return 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "hit_ratio": 0.0,
            "current_size": 0,
            "max_size": 0,
            "evictions": 0,
        }


# Global singleton instance provider
_global_query_cache: Optional[AbstractMemoryQueryCacheProvider] = None


def get_memory_query_cache() -> AbstractMemoryQueryCacheProvider:
    """Dependency injection helper returning singleton query cache provider."""
    global _global_query_cache
    if _global_query_cache is None:
        _global_query_cache = DefaultMemoryQueryCacheProvider()
    return _global_query_cache


def set_memory_query_cache(provider: AbstractMemoryQueryCacheProvider) -> None:
    """Override singleton cache provider (e.g. for testing)."""
    global _global_query_cache
    _global_query_cache = provider


__all__ = [
    "AbstractMemoryQueryCacheProvider",
    "DefaultMemoryQueryCacheProvider",
    "NullQueryCacheProvider",
    "get_memory_query_cache",
    "set_memory_query_cache",
]
