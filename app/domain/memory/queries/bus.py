"""
HunterOS Engage — Memory Query Bus

Central dispatcher routing Query Objects to dedicated Query Handlers
with automatic performance profiling, caching, and CQRS invariant enforcement.
"""

import time
from typing import Any, Dict, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.cache import AbstractMemoryQueryCacheProvider, get_memory_query_cache
from app.domain.memory.queries.engines.statistics import QueryMetricsTracker
from app.domain.memory.queries.handlers import AbstractQueryHandler
from app.domain.memory.queries.models import (
    BaseMemoryQuery,
    GetCustomerMemoryQuery,
    GetProjectionQuery,
    GetStatisticsQuery,
)


class MemoryQueryBus:
    """
    CQRS Query Bus responsible for dispatching queries to registered handlers.
    Strict Invariants:
    - Never opens a write transaction.
    - Never triggers domain events.
    - Never performs cache updates outside of read caching.
    """

    def __init__(self, cache_provider: Optional[AbstractMemoryQueryCacheProvider] = None) -> None:
        self._handlers: Dict[Type[BaseMemoryQuery], AbstractQueryHandler] = {}
        self._cache = cache_provider or get_memory_query_cache()
        self._tracker = QueryMetricsTracker.get_instance()

    def register(self, query_type: Type[BaseMemoryQuery], handler: AbstractQueryHandler) -> None:
        """Register a handler for a specific query object type."""
        self._handlers[query_type] = handler

    async def execute(self, query: BaseMemoryQuery, session: Optional[AsyncSession] = None) -> Any:
        """Dispatch query to handler with latency monitoring and caching."""
        query_type = type(query)
        handler = self._handlers.get(query_type)
        if not handler:
            raise KeyError(f"No query handler registered for query type {query_type.__name__}")

        start_time = time.perf_counter()

        # Handle caching for single-entity or projection lookups
        cache_key = None
        if not query.bypass_cache and isinstance(query, (GetCustomerMemoryQuery, GetProjectionQuery)):
            cache_key = self._cache.generate_cache_key(
                prefix=query_type.__name__.lower(),
                query_params=query.model_dump(mode="json"),
            )
            cached_result = await self._cache.get(cache_key)
            if cached_result is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                self._tracker.record_query(duration_ms=duration_ms, repo_duration_ms=0.0)
                return cached_result

        # Execute handler
        result = await handler.handle(query, session=session)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        self._tracker.record_query(duration_ms=duration_ms, repo_duration_ms=duration_ms)

        # Cache result if applicable
        if cache_key and result is not None:
            cid = getattr(query, "customer_id", None)
            wid = getattr(query, "workspace_id", None)
            await self._cache.set(
                key=cache_key,
                value=result,
                ttl_seconds=120,
                customer_id=cid,
                workspace_id=wid,
            )

        return result


__all__ = [
    "MemoryQueryBus",
]
