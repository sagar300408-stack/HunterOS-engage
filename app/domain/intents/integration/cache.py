"""
HunterOS Engage V1 - Intent Context Cache Abstraction
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Thread-safe cache abstractions for Intent Intelligence Context caching.
Provides in-memory fallback and no-op null implementations with zero external dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional

from app.domain.intents.integration.models import IntentIntelligenceContext


class IIntentContextCache(ABC):
    """Abstract interface for caching assembled Intent Intelligence Contexts."""

    @abstractmethod
    def get(self, key: str) -> Optional[IntentIntelligenceContext]:
        """Retrieve cached context by key if valid and unexpired."""
        pass

    @abstractmethod
    def set(self, key: str, context: IntentIntelligenceContext, ttl_seconds: Optional[int] = None) -> None:
        """Store context in cache with optional TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove context from cache by key."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Purge all entries from the cache."""
        pass


class NullIntentContextCache(IIntentContextCache):
    """Pass-through no-op cache implementation."""

    def get(self, key: str) -> Optional[IntentIntelligenceContext]:
        return None

    def set(self, key: str, context: IntentIntelligenceContext, ttl_seconds: Optional[int] = None) -> None:
        pass

    def delete(self, key: str) -> bool:
        return False

    def clear(self) -> None:
        pass


class InMemoryIntentContextCache(IIntentContextCache):
    """Thread-safe in-memory cache with optional TTL expiration."""

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self._lock = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[IntentIntelligenceContext]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None

            expires_at = entry.get("expires_at")
            if expires_at and datetime.now(timezone.utc) > expires_at:
                del self._store[key]
                return None

            return entry.get("context")

    def set(self, key: str, context: IntentIntelligenceContext, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            expires_at = None
            if ttl > 0:
                expires_at = datetime.now(timezone.utc).timestamp() + ttl
                expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)

            self._store[key] = {
                "context": context,
                "expires_at": expires_at,
            }

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
