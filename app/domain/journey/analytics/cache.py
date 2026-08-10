"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Analytics Cache Abstractions

Cache abstraction for analytics results. Cache must never affect correctness.
"""
from __future__ import annotations

import abc
import threading
from typing import Dict, Optional
import uuid

from app.domain.journey.analytics.models import JourneyAnalyticsResult


class IJourneyAnalyticsCache(abc.ABC):
    @abc.abstractmethod
    def get(self, cache_key: str) -> Optional[JourneyAnalyticsResult]: ...

    @abc.abstractmethod
    def set(self, cache_key: str, result: JourneyAnalyticsResult) -> None: ...

    @abc.abstractmethod
    def invalidate(self, cache_key: str) -> None: ...

    @abc.abstractmethod
    def clear(self) -> None: ...


class InMemoryJourneyAnalyticsCache(IJourneyAnalyticsCache):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: Dict[str, JourneyAnalyticsResult] = {}

    def get(self, cache_key: str) -> Optional[JourneyAnalyticsResult]:
        with self._lock:
            return self._store.get(cache_key)

    def set(self, cache_key: str, result: JourneyAnalyticsResult) -> None:
        with self._lock:
            self._store[cache_key] = result

    def invalidate(self, cache_key: str) -> None:
        with self._lock:
            self._store.pop(cache_key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class NullJourneyAnalyticsCache(IJourneyAnalyticsCache):
    """No-op cache — always misses. Used in tests or when caching is disabled."""
    def get(self, cache_key: str) -> Optional[JourneyAnalyticsResult]:
        return None
    def set(self, cache_key: str, result: JourneyAnalyticsResult) -> None:
        pass
    def invalidate(self, cache_key: str) -> None:
        pass
    def clear(self) -> None:
        pass
