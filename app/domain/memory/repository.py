"""
HunterOS Engage — Memory Repository Implementation

Concrete SQLAlchemy Async implementation of AbstractMemoryRepository.
Handles single & bulk persistence, versioning, timeline querying, change logging,
and multi-criteria search.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import (
    String,
    and_,
    cast,
    desc,
    func,
    or_,
    select,
    update as sa_update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.interfaces.repository import AbstractMemoryRepository
from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    MemoryChangeLog,
    MemoryImportance,
    MemoryTimelineCategory,
)


class MemoryRepository(AbstractMemoryRepository):
    """
    SQLAlchemy-backed repository for Customer Memory entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, memory_id: UUID, include_deleted: bool = False) -> Optional[CustomerMemory]:
        """Retrieve memory entity by memory ID."""
        stmt = select(CustomerMemory).where(CustomerMemory.id == memory_id)
        if not include_deleted:
            stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: UUID, include_deleted: bool = False) -> Optional[CustomerMemory]:
        """Retrieve memory entity by customer ID."""
        stmt = select(CustomerMemory).where(CustomerMemory.customer_id == customer_id)
        if not include_deleted:
            stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, memory: CustomerMemory) -> CustomerMemory:
        """Persist a new CustomerMemory entity."""
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def update(self, memory: CustomerMemory) -> CustomerMemory:
        """Update an existing CustomerMemory entity."""
        memory.updated_at = datetime.now(timezone.utc)
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def soft_delete(self, customer_id: UUID, deleted_at: Optional[datetime] = None) -> Optional[CustomerMemory]:
        """Soft-delete customer memory."""
        memory = await self.get_by_customer_id(customer_id, include_deleted=False)
        if not memory:
            return None
        memory.is_deleted = True
        memory.deleted_at = deleted_at or datetime.now(timezone.utc)
        memory.updated_at = datetime.now(timezone.utc)
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def restore(self, customer_id: UUID) -> Optional[CustomerMemory]:
        """Restore a soft-deleted customer memory."""
        memory = await self.get_by_customer_id(customer_id, include_deleted=True)
        if not memory:
            return None
        memory.is_deleted = False
        memory.deleted_at = None
        memory.updated_at = datetime.now(timezone.utc)
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def bulk_create(self, memories: List[CustomerMemory]) -> List[CustomerMemory]:
        """Bulk insert customer memories."""
        if not memories:
            return []
        self._session.add_all(memories)
        await self._session.flush()
        return memories

    async def bulk_get(self, customer_ids: List[UUID], include_deleted: bool = False) -> List[CustomerMemory]:
        """Bulk fetch customer memories by customer IDs."""
        if not customer_ids:
            return []
        stmt = select(CustomerMemory).where(CustomerMemory.customer_id.in_(customer_ids))
        if not include_deleted:
            stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_update(self, memories: List[CustomerMemory]) -> List[CustomerMemory]:
        """Bulk update customer memories."""
        if not memories:
            return []
        now = datetime.now(timezone.utc)
        for mem in memories:
            mem.updated_at = now
            self._session.add(mem)
        await self._session.flush()
        return memories

    async def create_version(self, version: CustomerMemoryVersion) -> CustomerMemoryVersion:
        """Persist an immutable memory version snapshot."""
        self._session.add(version)
        await self._session.flush()
        return version

    async def get_versions(self, customer_id: UUID, limit: int = 50, offset: int = 0) -> List[CustomerMemoryVersion]:
        """Retrieve version history for a customer."""
        stmt = (
            select(CustomerMemoryVersion)
            .where(CustomerMemoryVersion.customer_id == customer_id)
            .order_by(desc(CustomerMemoryVersion.version_number))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_version_by_number(self, customer_id: UUID, version_number: int) -> Optional[CustomerMemoryVersion]:
        """Retrieve a specific version snapshot by version number."""
        stmt = select(CustomerMemoryVersion).where(
            CustomerMemoryVersion.customer_id == customer_id,
            CustomerMemoryVersion.version_number == version_number,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_timeline_event(self, event: CustomerMemoryTimelineEvent) -> CustomerMemoryTimelineEvent:
        """Append an event to the customer memory timeline."""
        self._session.add(event)
        await self._session.flush()
        return event

    async def bulk_create_timeline_events(
        self, events: List[CustomerMemoryTimelineEvent]
    ) -> List[CustomerMemoryTimelineEvent]:
        """Bulk append events to the memory timeline."""
        if not events:
            return []
        self._session.add_all(events)
        await self._session.flush()
        return events

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
    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:
        """Retrieve filtered, paginated timeline events and total count."""
        base_conditions = [CustomerMemoryTimelineEvent.customer_id == customer_id]

        if category:
            base_conditions.append(CustomerMemoryTimelineEvent.category == category)
        if event_type:
            base_conditions.append(CustomerMemoryTimelineEvent.event_type == event_type)
        if importance:
            base_conditions.append(CustomerMemoryTimelineEvent.importance == importance)
        if start_time:
            base_conditions.append(CustomerMemoryTimelineEvent.created_at >= start_time)
        if end_time:
            base_conditions.append(CustomerMemoryTimelineEvent.created_at <= end_time)

        count_stmt = select(func.count(CustomerMemoryTimelineEvent.id)).where(and_(*base_conditions))
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one() or 0

        data_stmt = (
            select(CustomerMemoryTimelineEvent)
            .where(and_(*base_conditions))
            .order_by(desc(CustomerMemoryTimelineEvent.created_at))
            .limit(limit)
            .offset(offset)
        )
        data_result = await self._session.execute(data_stmt)
        items = list(data_result.scalars().all())

        return items, total

    async def create_change_logs(self, entries: List[MemoryChangeLog]) -> List[MemoryChangeLog]:
        """Bulk append granular field-level change logs."""
        if not entries:
            return []
        self._session.add_all(entries)
        await self._session.flush()
        return entries

    async def get_change_logs(
        self,
        customer_id: UUID,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[MemoryChangeLog], int]:
        """Retrieve field-level change logs for a customer."""
        conditions = [MemoryChangeLog.customer_id == customer_id]
        if version_number is not None:
            conditions.append(MemoryChangeLog.version_number == version_number)
        if field_path:
            conditions.append(MemoryChangeLog.field_path.ilike(f"%{field_path}%"))

        count_stmt = select(func.count(MemoryChangeLog.id)).where(and_(*conditions))
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one() or 0

        data_stmt = (
            select(MemoryChangeLog)
            .where(and_(*conditions))
            .order_by(desc(MemoryChangeLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        data_result = await self._session.execute(data_stmt)
        items = list(data_result.scalars().all())

        return items, total

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
    ) -> Tuple[List[CustomerMemory], int]:
        """
        Multi-criteria search across customer memory records.
        """
        conditions = [CustomerMemory.is_deleted == False]  # noqa: E712

        if workspace_id:
            conditions.append(CustomerMemory.workspace_id == workspace_id)

        # Text matching on JSON string
        if search_term:
            json_text = cast(CustomerMemory.memory_payload, String)
            conditions.append(
                or_(
                    json_text.ilike(f"%{search_term}%"),
                    cast(CustomerMemory.customer_id, String).ilike(f"%{search_term}%"),
                )
            )

        if location_city:
            json_text = cast(CustomerMemory.memory_payload, String)
            conditions.append(json_text.ilike(f"%{location_city}%"))

        if current_stage:
            json_text = cast(CustomerMemory.memory_payload, String)
            conditions.append(json_text.ilike(f"%{current_stage}%"))

        if tags:
            json_text = cast(CustomerMemory.memory_payload, String)
            tag_conds = [json_text.ilike(f"%{t}%") for t in tags]
            conditions.append(or_(*tag_conds))

        if property_types:
            json_text = cast(CustomerMemory.memory_payload, String)
            prop_conds = [json_text.ilike(f"%{pt}%") for pt in property_types]
            conditions.append(or_(*prop_conds))

        count_stmt = select(func.count(CustomerMemory.id)).where(and_(*conditions))
        count_res = await self._session.execute(count_stmt)
        total = count_res.scalar_one() or 0

        data_stmt = (
            select(CustomerMemory)
            .where(and_(*conditions))
            .order_by(desc(CustomerMemory.updated_at))
            .limit(limit)
            .offset(offset)
        )
        data_res = await self._session.execute(data_stmt)
        items = list(data_res.scalars().all())

        return items, total
