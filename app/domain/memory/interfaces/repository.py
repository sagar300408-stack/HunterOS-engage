"""
Memory Domain - Abstract Repository Interface
"""

import abc
from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import UUID


class AbstractMemoryRepository(abc.ABC):
    """
    Abstract interface defining data access operations for the Customer Memory domain.
    Decouples storage engines from domain service logic.
    """

    @abc.abstractmethod
    async def get_by_id(self, memory_id: UUID, include_deleted: bool = False) -> Optional[Any]:
        """Retrieve memory entity by memory ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_customer_id(self, customer_id: UUID, include_deleted: bool = False) -> Optional[Any]:
        """Retrieve memory entity by customer ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def create(self, memory: Any) -> Any:
        """Persist a new CustomerMemory entity."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, memory: Any) -> Any:
        """Update an existing CustomerMemory entity."""
        raise NotImplementedError

    @abc.abstractmethod
    async def soft_delete(self, customer_id: UUID, deleted_at: datetime) -> Optional[Any]:
        """Soft-delete customer memory."""
        raise NotImplementedError

    @abc.abstractmethod
    async def restore(self, customer_id: UUID) -> Optional[Any]:
        """Restore a soft-deleted customer memory."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_create(self, memories: List[Any]) -> List[Any]:
        """Bulk insert customer memories."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_get(self, customer_ids: List[UUID], include_deleted: bool = False) -> List[Any]:
        """Bulk fetch customer memories by customer IDs."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_update(self, memories: List[Any]) -> List[Any]:
        """Bulk update customer memories."""
        raise NotImplementedError

    @abc.abstractmethod
    async def create_version(self, version: Any) -> Any:
        """Persist an immutable memory version snapshot."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_versions(self, customer_id: UUID, limit: int = 50, offset: int = 0) -> List[Any]:
        """Retrieve version history for a customer."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_version_by_number(self, customer_id: UUID, version_number: int) -> Optional[Any]:
        """Retrieve a specific version snapshot by version number."""
        raise NotImplementedError

    @abc.abstractmethod
    async def create_timeline_event(self, event: Any) -> Any:
        """Append an event to the customer memory timeline."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_create_timeline_events(self, events: List[Any]) -> List[Any]:
        """Bulk append events to the memory timeline."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_timeline(
        self,
        customer_id: UUID,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
        importance: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Any], int]:
        """Retrieve filtered, paginated timeline events and total count."""
        raise NotImplementedError

    @abc.abstractmethod
    async def create_change_logs(self, entries: List[Any]) -> List[Any]:
        """Bulk append granular field-level change logs."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_change_logs(
        self,
        customer_id: UUID,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Any], int]:
        """Retrieve field-level change logs for a customer."""
        raise NotImplementedError

    @abc.abstractmethod
    async def search_memories(
        self,
        workspace_id: Optional[UUID] = None,
        search_term: Optional[str] = None,
        current_stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        location_city: Optional[str] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        property_types: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Any], int]:
        """Multi-criteria search over customer memory records."""
        raise NotImplementedError
