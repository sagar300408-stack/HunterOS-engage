"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity Cache Interface and Implementations
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
import threading
from typing import Dict, Optional, Tuple
import uuid

from app.domain.journey.maturity.models import JourneyMaturityResult


class IJourneyMaturityCache(abc.ABC):
    """Abstract interface for optional maturity calculation caching."""

    @abc.abstractmethod
    def get(self, journey_id: uuid.UUID) -> Optional[JourneyMaturityResult]:
        pass

    @abc.abstractmethod
    def set(self, journey_id: uuid.UUID, result: JourneyMaturityResult, ttl_seconds: int = 300) -> None:
        pass

    @abc.abstractmethod
    def invalidate(self, journey_id: uuid.UUID) -> None:
        pass

    @abc.abstractmethod
    def clear(self) -> None:
        pass


class InMemoryJourneyMaturityCache(IJourneyMaturityCache):
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: Dict[str, Tuple[JourneyMaturityResult, float]] = {}

    def _key(self, journey_id: uuid.UUID) -> str:
        return str(journey_id)

    def get(self, journey_id: uuid.UUID) -> Optional[JourneyMaturityResult]:
        with self._lock:
            key = self._key(journey_id)
            if key not in self._entries:
                return None
            result, expire_at = self._entries[key]
            if datetime.now(timezone.utc).timestamp() > expire_at:
                del self._entries[key]
                return None
            return result

    def set(self, journey_id: uuid.UUID, result: JourneyMaturityResult, ttl_seconds: int = 300) -> None:
        with self._lock:
            key = self._key(journey_id)
            expire_at = datetime.now(timezone.utc).timestamp() + ttl_seconds
            self._entries[key] = (result, expire_at)

    def invalidate(self, journey_id: uuid.UUID) -> None:
        with self._lock:
            self._entries.pop(self._key(journey_id), None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class NullJourneyMaturityCache(IJourneyMaturityCache):
    """No-op pass-through cache implementation."""

    def get(self, journey_id: uuid.UUID) -> Optional[JourneyMaturityResult]:
        return None

    def set(self, journey_id: uuid.UUID, result: JourneyMaturityResult, ttl_seconds: int = 300) -> None:
        pass

    def invalidate(self, journey_id: uuid.UUID) -> None:
        pass

    def clear(self) -> None:
        pass
