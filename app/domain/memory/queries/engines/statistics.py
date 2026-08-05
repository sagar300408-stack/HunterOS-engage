"""
HunterOS Engage — Memory Statistics & Operational Metrics Engine

Computes aggregate memory domain analytics (lifecycle distributions, storage metrics,
version metrics, growth trends) and monitors operational query performance.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.cache import AbstractMemoryQueryCacheProvider, get_memory_query_cache
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.models import (
    GetStatisticsQuery,
    MemoryStatisticsDTO,
    OperationalMetricsDTO,
)


class QueryMetricsTracker:
    """Thread-safe operational telemetry collector for memory query execution."""

    _instance: Optional["QueryMetricsTracker"] = None
    _lock = asyncio.Lock()

    def __init__(self, slow_query_threshold_ms: float = 200.0) -> None:
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.total_queries = 0
        self.total_query_time_ms = 0.0
        self.slow_queries = 0
        self.total_repo_time_ms = 0.0

    @classmethod
    def get_instance(cls) -> "QueryMetricsTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_query(self, duration_ms: float, repo_duration_ms: float = 0.0) -> None:
        self.total_queries += 1
        self.total_query_time_ms += duration_ms
        self.total_repo_time_ms += repo_duration_ms
        if duration_ms >= self.slow_query_threshold_ms:
            self.slow_queries += 1

    def get_operational_metrics(self, cache_provider: Optional[AbstractMemoryQueryCacheProvider] = None) -> OperationalMetricsDTO:
        cache = cache_provider or get_memory_query_cache()
        cache_stats = cache.get_stats()

        avg_query_time = (self.total_query_time_ms / self.total_queries) if self.total_queries > 0 else 0.0
        avg_repo_time = (self.total_repo_time_ms / self.total_queries) if self.total_queries > 0 else 0.0

        return OperationalMetricsDTO(
            total_queries_executed=self.total_queries,
            average_query_time_ms=round(avg_query_time, 2),
            slow_queries_count=self.slow_queries,
            cache_hit_ratio=cache_stats.get("hit_ratio", 0.0),
            repository_execution_time_ms=round(avg_repo_time, 2),
            active_cache_entries=cache_stats.get("current_size", 0),
        )

    def reset(self) -> None:
        self.total_queries = 0
        self.total_query_time_ms = 0.0
        self.slow_queries = 0
        self.total_repo_time_ms = 0.0


class MemoryStatisticsEngine:
    """
    Computes domain and operational statistics for the memory subsystem.
    Executes purely read-only aggregation queries against the repository.
    """

    def __init__(
        self,
        repository: AbstractMemoryReadRepository,
        cache_provider: Optional[AbstractMemoryQueryCacheProvider] = None,
    ) -> None:
        self._repo = repository
        self._cache = cache_provider or get_memory_query_cache()
        self._tracker = QueryMetricsTracker.get_instance()

    async def get_statistics(
        self,
        query: GetStatisticsQuery,
        session: Optional[AsyncSession] = None,
    ) -> MemoryStatisticsDTO:
        """Compute aggregated business statistics and attach operational metrics."""
        cache_key = self._cache.generate_cache_key(
            prefix="stats",
            query_params={"workspace_id": str(query.workspace_id) if query.workspace_id else None},
        )

        if not query.bypass_cache:
            cached = await self._cache.get(cache_key)
            if cached and isinstance(cached, dict):
                dto = MemoryStatisticsDTO.model_validate(cached)
                if query.include_operational_metrics:
                    op_metrics = self._tracker.get_operational_metrics(self._cache)
                    dto = dto.model_copy(update={"operational_metrics": op_metrics})
                return dto

        # Fetch aggregated metrics from repository
        start_time = time.perf_counter()
        raw_stats = await self._repo.aggregate_memory_statistics(
            workspace_id=query.workspace_id,
            session=session,
        )
        repo_time_ms = (time.perf_counter() - start_time) * 1000.0

        op_metrics = self._tracker.get_operational_metrics(self._cache) if query.include_operational_metrics else None

        dto = MemoryStatisticsDTO(
            total_memories=raw_stats.get("total_memories", 0),
            active_count=raw_stats.get("active_count", 0),
            archived_count=raw_stats.get("archived_count", 0),
            locked_count=raw_stats.get("locked_count", 0),
            deleted_count=raw_stats.get("deleted_count", 0),
            migrating_count=raw_stats.get("migrating_count", 0),
            avg_versions_per_memory=raw_stats.get("avg_versions_per_memory", 1.0),
            max_versions_count=raw_stats.get("max_versions_count", 1),
            estimated_storage_bytes=raw_stats.get("estimated_storage_bytes", 0),
            avg_payload_bytes=raw_stats.get("avg_payload_bytes", 0.0),
            lifecycle_distribution=raw_stats.get("lifecycle_distribution", {}),
            top_cities=raw_stats.get("top_cities", {}),
            top_tags=raw_stats.get("top_tags", {}),
            growth_time_series=raw_stats.get("growth_time_series", []),
            operational_metrics=op_metrics,
        )

        # Cache business statistics (TTL = 60 seconds)
        await self._cache.set(
            key=cache_key,
            value=dto.model_dump(mode="json"),
            ttl_seconds=60,
            workspace_id=query.workspace_id,
        )

        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        self._tracker.record_query(total_time_ms, repo_time_ms)

        return dto


__all__ = [
    "QueryMetricsTracker",
    "MemoryStatisticsEngine",
]
