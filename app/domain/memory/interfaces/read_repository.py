"""
HunterOS Engage — Abstract Memory Read Repository (CQRS)

Query interface for reading memory aggregates, historical versions,
timeline events, field-level change logs, specifications, and analytics aggregation.
"""

import abc
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    LifecycleStatus,
    MemoryChangeLog,
    MemoryImportance,
    MemoryTimelineCategory,
)


class AbstractMemoryReadRepository(abc.ABC):
    """Abstract query repository for Customer Memory domain."""

    @abc.abstractmethod
    def get_model_class(self) -> Type[CustomerMemory]:
        """Return the underlying SQLAlchemy model class."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_customer_id(
        self,
        customer_id: UUID,
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[CustomerMemory]:
        """Fetch CustomerMemory by customer UUID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_id(
        self,
        memory_id: UUID,
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[CustomerMemory]:
        """Fetch CustomerMemory by primary key ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_multiple(
        self,
        customer_ids: List[UUID],
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> List[CustomerMemory]:
        """Bulk fetch CustomerMemory records by customer UUID list."""
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_query_plan_offset(
        self,
        plan: Any,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], int]:
        """Execute a compiled QueryExecutionPlan with offset pagination."""
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_query_plan_cursor(
        self,
        plan: Any,
        expected_workspace_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], bool, Optional[str], Optional[str]]:
        """Execute a compiled QueryExecutionPlan with workspace-isolated keyset cursor pagination."""
        raise NotImplementedError

    @abc.abstractmethod
    async def aggregate_memory_statistics(
        self,
        workspace_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Compute aggregated lifecycle distributions, storage sizing, and growth metrics."""
        raise NotImplementedError

    # ── Legacy & Sub-Entity Read Methods ───────────────────────────────────────

    @abc.abstractmethod
    async def search(
        self,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[UUID] = None,
        search_term: Optional[str] = None,
        current_stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        location_city: Optional[str] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        property_types: Optional[List[str]] = None,
        lifecycle_status: Optional[LifecycleStatus] = None,
        page: int = 1,
        page_size: int = 50,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemory], int]:
        """Multi-criteria search across memory records."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_timeline(
        self,
        customer_id: UUID,
        category: Optional[MemoryTimelineCategory] = None,
        event_type: Optional[str] = None,
        importance: Optional[MemoryImportance] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:
        """Retrieve paginated timeline events."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_versions(
        self,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 50,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryVersion], int]:
        """Retrieve paginated version history."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_version_by_number(
        self,
        customer_id: UUID,
        version_number: int,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Optional[CustomerMemoryVersion]:
        """Retrieve a specific immutable version snapshot."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_change_logs(
        self,
        customer_id: UUID,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[MemoryChangeLog], int]:
        """Retrieve granular field-level change history."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_get(
        self,
        customer_ids: List[UUID],
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> List[CustomerMemory]:
        """Bulk fetch memory aggregates by customer UUIDs."""
        raise NotImplementedError


__all__ = [
    "AbstractMemoryReadRepository",
]
