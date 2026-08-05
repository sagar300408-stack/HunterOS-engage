"""
HunterOS Engage — Memory Query Facade

Unified entry point orchestrating all memory read sub-engines, query handlers,
and query bus dispatching while guaranteeing strict CQRS read-only semantics.
"""

from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.cache import AbstractMemoryQueryCacheProvider, get_memory_query_cache
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.bus import MemoryQueryBus
from app.domain.memory.queries.engines.export import MemoryExportEngine
from app.domain.memory.queries.engines.projection import (
    MemoryProjectionEngine,
    ProjectionRegistry,
)
from app.domain.memory.queries.engines.search import (
    MemorySearchEngine,
    SearchCompiler,
)
from app.domain.memory.queries.engines.statistics import (
    MemoryStatisticsEngine,
    QueryMetricsTracker,
)
from app.domain.memory.queries.filters import FilterGroup
from app.domain.memory.queries.handlers import (
    BulkGetCustomerMemoryHandler,
    ExportPreviewHandler,
    GetCursorPaginatedMemoryHandler,
    GetCustomerMemoryHandler,
    GetProjectionHandler,
    GetStatisticsHandler,
    SearchCustomerMemoryHandler,
)
from app.domain.memory.queries.models import (
    BaseMemoryQuery,
    BulkGetCustomerMemoryQuery,
    CustomerMemoryDTO,
    ExportPreviewQuery,
    GetCursorPaginatedMemoryQuery,
    GetCustomerMemoryQuery,
    GetProjectionQuery,
    GetStatisticsQuery,
    MemoryExportDTO,
    MemoryStatisticsDTO,
    ProjectedMemoryDTO,
    SearchCustomerMemoryQuery,
)
from app.domain.memory.queries.pagination import (
    CursorPaginatedResult,
    OffsetPaginatedResult,
)
from app.domain.memory.queries.sorting import SortField
from app.domain.memory.queries.specifications import Specification


class MemoryQueryFacade:
    """
    Unified high-level facade for all Customer Memory read operations.
    Acts as the single point of entry for queries, routing through MemoryQueryBus.
    """

    def __init__(
        self,
        repository: AbstractMemoryReadRepository,
        cache_provider: Optional[AbstractMemoryQueryCacheProvider] = None,
    ) -> None:
        self._repo = repository
        self._cache = cache_provider or get_memory_query_cache()

        # Initialize specialized sub-engines
        self._search_engine = MemorySearchEngine(self._repo)
        self._projection_engine = MemoryProjectionEngine()
        self._statistics_engine = MemoryStatisticsEngine(self._repo, self._cache)
        self._export_engine = MemoryExportEngine(self._repo)

        # Initialize query bus & register handlers
        self._bus = MemoryQueryBus(self._cache)
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register query handlers with query bus."""
        self._bus.register(GetCustomerMemoryQuery, GetCustomerMemoryHandler(self._repo))
        self._bus.register(BulkGetCustomerMemoryQuery, BulkGetCustomerMemoryHandler(self._repo))
        self._bus.register(SearchCustomerMemoryQuery, SearchCustomerMemoryHandler(self._search_engine))
        self._bus.register(GetCursorPaginatedMemoryQuery, GetCursorPaginatedMemoryHandler(self._search_engine))
        self._bus.register(GetProjectionQuery, GetProjectionHandler(self._repo, self._projection_engine))
        self._bus.register(GetStatisticsQuery, GetStatisticsHandler(self._statistics_engine))
        self._bus.register(ExportPreviewQuery, ExportPreviewHandler(self._export_engine))

    @property
    def bus(self) -> MemoryQueryBus:
        """Direct access to query bus."""
        return self._bus

    @property
    def projection_registry(self) -> type[ProjectionRegistry]:
        """Direct access to projection registry."""
        return ProjectionRegistry

    async def execute(self, query: BaseMemoryQuery, session: Optional[AsyncSession] = None) -> Any:
        """Execute any Query Object via the Query Bus."""
        return await self._bus.execute(query, session=session)

    # ── High-Level Query Methods ──────────────────────────────────────────────

    async def get_customer_memory(
        self,
        customer_id: UUID,
        include_deleted: bool = False,
        include_locked: bool = True,
        bypass_cache: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[CustomerMemoryDTO]:
        """Fetch single customer memory by ID."""
        query = GetCustomerMemoryQuery(
            customer_id=customer_id,
            include_deleted=include_deleted,
            include_locked=include_locked,
            bypass_cache=bypass_cache,
        )
        return await self._bus.execute(query, session=session)

    async def bulk_get_customer_memories(
        self,
        customer_ids: List[UUID],
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> List[CustomerMemoryDTO]:
        """Fetch multiple customer memory records by ID list."""
        query = BulkGetCustomerMemoryQuery(
            customer_ids=customer_ids,
            include_deleted=include_deleted,
        )
        return await self._bus.execute(query, session=session)

    async def search_memories(
        self,
        workspace_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        location_city: Optional[str] = None,
        current_stage: Optional[str] = None,
        property_types: Optional[List[str]] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        lifecycle_status: Optional[str] = None,
        search_term: Optional[str] = None,
        custom_filters: Optional[FilterGroup] = None,
        specifications: Optional[List[Specification]] = None,
        sort_by: Optional[List[SortField]] = None,
        page: int = 1,
        page_size: int = 50,
        session: Optional[AsyncSession] = None,
    ) -> OffsetPaginatedResult[CustomerMemoryDTO]:
        """Execute multi-criteria search using unified search pipeline."""
        compiled_filters = SearchCompiler.compile_search_params(
            workspace_id=workspace_id,
            tags=tags,
            location_city=location_city,
            current_stage=current_stage,
            property_types=property_types,
            min_budget=min_budget,
            max_budget=max_budget,
            lifecycle_status=lifecycle_status,
            search_term=search_term,
            custom_filters=custom_filters,
        )

        query = SearchCustomerMemoryQuery(
            workspace_id=workspace_id,
            filter_group=compiled_filters,
            specifications=specifications,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        return await self._bus.execute(query, session=session)

    async def search_memories_cursor(
        self,
        workspace_id: Optional[UUID] = None,
        custom_filters: Optional[FilterGroup] = None,
        specifications: Optional[List[Specification]] = None,
        sort_by: Optional[List[SortField]] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
        session: Optional[AsyncSession] = None,
    ) -> CursorPaginatedResult[CustomerMemoryDTO]:
        """Execute keyset cursor-paginated search."""
        query = GetCursorPaginatedMemoryQuery(
            workspace_id=workspace_id,
            filter_group=custom_filters,
            specifications=specifications,
            sort_by=sort_by,
            cursor=cursor,
            limit=limit,
        )
        return await self._bus.execute(query, session=session)

    async def get_projection(
        self,
        customer_id: UUID,
        view_name: Optional[str] = None,
        projection_mask: Optional[List[str]] = None,
        projection_version: str = "1.0.0",
        bypass_cache: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Any]:
        """Retrieve shaped or masked projection view for customer memory."""
        query = GetProjectionQuery(
            customer_id=customer_id,
            view_name=view_name,
            projection_mask=projection_mask,
            projection_version=projection_version,
            bypass_cache=bypass_cache,
        )
        return await self._bus.execute(query, session=session)

    async def get_statistics(
        self,
        workspace_id: Optional[UUID] = None,
        include_operational_metrics: bool = True,
        bypass_cache: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> MemoryStatisticsDTO:
        """Compute memory domain statistics and operational metrics."""
        query = GetStatisticsQuery(
            workspace_id=workspace_id,
            include_operational_metrics=include_operational_metrics,
            bypass_cache=bypass_cache,
        )
        return await self._bus.execute(query, session=session)

    async def preview_export(
        self,
        workspace_id: Optional[UUID] = None,
        custom_filters: Optional[FilterGroup] = None,
        specifications: Optional[List[Specification]] = None,
        export_format: str = "CSV",
        columns: Optional[List[str]] = None,
        max_rows: int = 100,
        session: Optional[AsyncSession] = None,
    ) -> MemoryExportDTO:
        """Generate flat tabular export preview dataset."""
        query = ExportPreviewQuery(
            workspace_id=workspace_id,
            filter_group=custom_filters,
            specifications=specifications,
            export_format=export_format,
            columns=columns,
            max_rows=max_rows,
        )
        return await self._bus.execute(query, session=session)

    async def invalidate_customer_cache(self, customer_id: UUID) -> int:
        """Invalidate all cached queries for a specific customer upon write events."""
        return await self._cache.invalidate_customer(customer_id)

    async def invalidate_workspace_cache(self, workspace_id: UUID) -> int:
        """Invalidate all cached queries for a workspace upon write events."""
        return await self._cache.invalidate_workspace(workspace_id)


__all__ = [
    "MemoryQueryFacade",
]
