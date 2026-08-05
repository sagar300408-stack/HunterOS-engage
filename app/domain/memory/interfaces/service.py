"""
HunterOS Engage — Memory Domain Abstract Service Interface
"""

import abc
from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import UUID


class AbstractMemoryService(abc.ABC):
    """
    Abstract interface for Customer Memory domain operations.
    Encapsulates domain logic, versioning, change tracking, timeline generation,
    and history aggregation.
    """

    @abc.abstractmethod
    async def create_customer_memory(self, request: Any, session: Any) -> Any:
        """Create a new customer memory record and baseline version."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_customer_memory(
        self, customer_id: UUID, include_deleted: bool = False, session: Any = None
    ) -> Optional[Any]:
        """Retrieve active or soft-deleted customer memory."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update_customer_memory(self, customer_id: UUID, request: Any, session: Any) -> Any:
        """
        Update customer memory fields (PATCH).
        Must atomically create a version snapshot, change log entries, and timeline events.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def replace_customer_memory(self, customer_id: UUID, request: Any, session: Any) -> Any:
        """
        Completely replace customer memory fields (PUT).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def soft_delete_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = None,
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Soft-delete memory and record audit trail."""
        raise NotImplementedError

    @abc.abstractmethod
    async def restore_memory(
        self,
        customer_id: UUID,
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Restore soft-deleted memory and record audit trail."""
        raise NotImplementedError

    @abc.abstractmethod
    async def change_lifecycle_status(
        self,
        customer_id: UUID,
        target_status: Any,
        reason: Optional[str] = None,
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Transition customer memory lifecycle status."""
        raise NotImplementedError

    @abc.abstractmethod
    async def lock_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Administrative lock",
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Lock customer memory."""
        raise NotImplementedError

    @abc.abstractmethod
    async def unlock_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Administrative unlock",
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Unlock customer memory."""
        raise NotImplementedError

    @abc.abstractmethod
    async def archive_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Archival transition",
        changed_by: Optional[str] = None,
        session: Any = None,
    ) -> Any:
        """Archive customer memory."""
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
        page: int = 1,
        page_size: int = 50,
        session: Any = None,
    ) -> Tuple[List[Any], int]:
        """Retrieve paginated timeline events."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_versions(
        self, customer_id: UUID, page: int = 1, page_size: int = 50, session: Any = None
    ) -> Tuple[List[Any], int]:
        """Retrieve version history summaries."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_version_by_number(
        self, customer_id: UUID, version_number: int, session: Any = None
    ) -> Optional[Any]:
        """Retrieve full immutable version snapshot."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_change_logs(
        self,
        customer_id: UUID,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        session: Any = None,
    ) -> Tuple[List[Any], int]:
        """Retrieve field-level change history."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_customer_memory_history(self, customer_id: UUID, session: Any = None) -> Any:
        """
        Unified history query returning memory, timeline, versions, and change logs
        in a single payload.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def search_memory(self, request: Any, session: Any = None) -> Any:
        """Perform multi-criteria memory search."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_create_memories(self, requests: List[Any], session: Any) -> List[Any]:
        """Bulk initialize customer memories."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_get_memories(
        self, customer_ids: List[UUID], include_deleted: bool = False, session: Any = None
    ) -> List[Any]:
        """Bulk retrieve customer memories."""
        raise NotImplementedError

    @abc.abstractmethod
    async def bulk_update_memories(self, requests: List[Any], session: Any) -> List[Any]:
        """Bulk update customer memories."""
        raise NotImplementedError
