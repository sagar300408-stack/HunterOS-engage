"""
HunterOS Engage — Memory Query Handlers

Implements dedicated query handler classes processing Query Objects,
interacting with specialized sub-engines, and returning immutable Read Model DTOs.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.cache import AbstractMemoryQueryCacheProvider, get_memory_query_cache
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.engines.export import MemoryExportEngine
from app.domain.memory.queries.engines.projection import MemoryProjectionEngine
from app.domain.memory.queries.engines.search import MemorySearchEngine
from app.domain.memory.queries.engines.statistics import MemoryStatisticsEngine
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
from app.domain.memory.queries.pagination import CursorPaginatedResult, OffsetPaginatedResult


Q = TypeVar("Q", bound=BaseMemoryQuery)
R = TypeVar("R")


class AbstractQueryHandler(ABC, Generic[Q, R]):
    """Abstract base class for memory query handlers."""

    @abstractmethod
    async def handle(self, query: Q, session: Optional[AsyncSession] = None) -> R:
        """Process query object and return immutable read model."""
        raise NotImplementedError


class GetCustomerMemoryHandler(AbstractQueryHandler[GetCustomerMemoryQuery, Optional[CustomerMemoryDTO]]):
    """Handles fetching a single customer memory by ID."""

    def __init__(self, repository: AbstractMemoryReadRepository) -> None:
        self._repo = repository

    async def handle(self, query: GetCustomerMemoryQuery, session: Optional[AsyncSession] = None) -> Optional[CustomerMemoryDTO]:
        entity = await self._repo.get_by_customer_id(
            customer_id=query.customer_id,
            include_deleted=query.include_deleted,
            session=session,
        )
        if not entity:
            return None

        dto = MemorySearchEngine._to_dto(entity)
        if not query.include_locked and dto.lifecycle_status == "LOCKED":
            return None
        return dto


class BulkGetCustomerMemoryHandler(AbstractQueryHandler[BulkGetCustomerMemoryQuery, List[CustomerMemoryDTO]]):
    """Handles fetching multiple customer memories by ID list."""

    def __init__(self, repository: AbstractMemoryReadRepository) -> None:
        self._repo = repository

    async def handle(self, query: BulkGetCustomerMemoryQuery, session: Optional[AsyncSession] = None) -> List[CustomerMemoryDTO]:
        entities = await self._repo.get_multiple(
            customer_ids=query.customer_ids,
            include_deleted=query.include_deleted,
            session=session,
        )
        return [MemorySearchEngine._to_dto(e) for e in entities]


class SearchCustomerMemoryHandler(AbstractQueryHandler[SearchCustomerMemoryQuery, OffsetPaginatedResult[CustomerMemoryDTO]]):
    """Handles multi-criteria search queries via MemorySearchEngine."""

    def __init__(self, search_engine: MemorySearchEngine) -> None:
        self._engine = search_engine

    async def handle(
        self,
        query: SearchCustomerMemoryQuery,
        session: Optional[AsyncSession] = None,
    ) -> OffsetPaginatedResult[CustomerMemoryDTO]:
        return await self._engine.search_offset(query, session=session)


class GetCursorPaginatedMemoryHandler(AbstractQueryHandler[GetCursorPaginatedMemoryQuery, CursorPaginatedResult[CustomerMemoryDTO]]):
    """Handles keyset cursor-paginated queries via MemorySearchEngine."""

    def __init__(self, search_engine: MemorySearchEngine) -> None:
        self._engine = search_engine

    async def handle(
        self,
        query: GetCursorPaginatedMemoryQuery,
        session: Optional[AsyncSession] = None,
    ) -> CursorPaginatedResult[CustomerMemoryDTO]:
        return await self._engine.search_cursor(query, session=session)


class GetProjectionHandler(AbstractQueryHandler[GetProjectionQuery, Optional[Any]]):
    """Handles field-masking and versioned view projection requests."""

    def __init__(
        self,
        repository: AbstractMemoryReadRepository,
        projection_engine: MemoryProjectionEngine,
    ) -> None:
        self._repo = repository
        self._engine = projection_engine

    async def handle(self, query: GetProjectionQuery, session: Optional[AsyncSession] = None) -> Optional[Any]:
        entity = await self._repo.get_by_customer_id(
            customer_id=query.customer_id,
            include_deleted=False,
            session=session,
        )
        if not entity:
            return None

        dto = MemorySearchEngine._to_dto(entity)
        return self._engine.project(
            memory=dto,
            view_name=query.view_name,
            projection_mask=query.projection_mask,
            projection_version=query.projection_version,
        )


class GetStatisticsHandler(AbstractQueryHandler[GetStatisticsQuery, MemoryStatisticsDTO]):
    """Handles domain and operational statistics aggregation."""

    def __init__(self, statistics_engine: MemoryStatisticsEngine) -> None:
        self._engine = statistics_engine

    async def handle(self, query: GetStatisticsQuery, session: Optional[AsyncSession] = None) -> MemoryStatisticsDTO:
        return await self._engine.get_statistics(query, session=session)


class ExportPreviewHandler(AbstractQueryHandler[ExportPreviewQuery, MemoryExportDTO]):
    """Handles tabular export preview generation."""

    def __init__(self, export_engine: MemoryExportEngine) -> None:
        self._engine = export_engine

    async def handle(self, query: ExportPreviewQuery, session: Optional[AsyncSession] = None) -> MemoryExportDTO:
        return await self._engine.preview_export(query, session=session)


__all__ = [
    "AbstractQueryHandler",
    "GetCustomerMemoryHandler",
    "BulkGetCustomerMemoryHandler",
    "SearchCustomerMemoryHandler",
    "GetCursorPaginatedMemoryHandler",
    "GetProjectionHandler",
    "GetStatisticsHandler",
    "ExportPreviewHandler",
]
