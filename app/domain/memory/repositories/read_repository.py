"""
HunterOS Engage — SQLAlchemy Memory Read Repository (CQRS)

High-performance, strictly read-only repository implementing compiled specification execution,
keyset cursor pagination, advanced aggregation metrics, and historical snapshot retrieval.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID
from sqlalchemy import (
    and_,
    asc,
    cast,
    desc,
    func,
    or_,
    select,
    String,
    Float,
    Integer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    LifecycleStatus,
    MemoryChangeLog,
    MemoryImportance,
    MemoryTimelineCategory,
)
from app.domain.memory.queries.pagination import CursorCodec, CursorPaginationParams, OffsetPaginationParams
from app.domain.memory.queries.planner import QueryExecutionPlan
from app.integrations.postgres.database import get_session_factory


class SqlAlchemyMemoryReadRepository(AbstractMemoryReadRepository):
    """
    SQLAlchemy Read Repository for CustomerMemory domain.
    All operations are strictly read-only and never mutate aggregate state.
    """

    def __init__(self, session_factory: Optional[Any] = None) -> None:
        self._session_factory = session_factory or get_session_factory

    def get_model_class(self) -> Type[CustomerMemory]:
        return CustomerMemory

    async def _resolve_session(self, session: Optional[AsyncSession]) -> Tuple[AsyncSession, bool]:
        """Resolves existing session or creates a temporary read-only session."""
        if session is not None:
            return session, False
        new_session = self._session_factory()
        return new_session, True

    async def get_by_customer_id(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[CustomerMemory]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_id: Optional[UUID] = kwargs.get("customer_id")
        include_deleted: bool = kwargs.get("include_deleted", False)
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_id = args[1]
                if len(args) > 2:
                    include_deleted = args[2]
            else:
                customer_id = args[0]
                if len(args) > 1:
                    if isinstance(args[1], bool):
                        include_deleted = args[1]
                    elif isinstance(args[1], AsyncSession):
                        session = args[1]
                if len(args) > 2 and isinstance(args[2], AsyncSession):
                    session = args[2]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemory).where(CustomerMemory.customer_id == customer_id)
            if workspace_id:
                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)
            if not include_deleted:
                stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
            res = await sess.execute(stmt)
            return res.scalar_one_or_none()
        finally:
            if is_temp:
                await sess.close()

    async def get_by_id(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[CustomerMemory]:
        session: Optional[AsyncSession] = kwargs.get("session")
        memory_id: Optional[UUID] = kwargs.get("memory_id")
        include_deleted: bool = kwargs.get("include_deleted", False)
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    memory_id = args[1]
                if len(args) > 2:
                    include_deleted = args[2]
            else:
                memory_id = args[0]
                if len(args) > 1:
                    if isinstance(args[1], bool):
                        include_deleted = args[1]
                    elif isinstance(args[1], AsyncSession):
                        session = args[1]
                if len(args) > 2 and isinstance(args[2], AsyncSession):
                    session = args[2]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemory).where(CustomerMemory.id == memory_id)
            if workspace_id:
                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)
            if workspace_id:
                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)
            if not include_deleted:
                stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
            res = await sess.execute(stmt)
            return res.scalar_one_or_none()
        finally:
            if is_temp:
                await sess.close()

    async def get_multiple(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> List[CustomerMemory]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_ids: List[UUID] = kwargs.get("customer_ids", [])
        include_deleted: bool = kwargs.get("include_deleted", False)
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_ids = args[1]
                if len(args) > 2:
                    include_deleted = args[2]
            else:
                customer_ids = args[0]
                if len(args) > 1:
                    if isinstance(args[1], bool):
                        include_deleted = args[1]
                    elif isinstance(args[1], AsyncSession):
                        session = args[1]
                if len(args) > 2 and isinstance(args[2], AsyncSession):
                    session = args[2]

        if not customer_ids:
            return []
        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemory).where(CustomerMemory.customer_id.in_(customer_ids))
            if workspace_id:
                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)
            if not include_deleted:
                stmt = stmt.where(CustomerMemory.is_deleted == False)  # noqa: E712
            res = await sess.execute(stmt)
            return list(res.scalars().all())
        finally:
            if is_temp:
                await sess.close()

    async def bulk_get(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> List[CustomerMemory]:
        return await self.get_multiple(*args, **kwargs)

    # ── Compiled Execution Plan Methods ───────────────────────────────────────

    async def execute_query_plan_offset(
        self,
        plan: QueryExecutionPlan,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], int]:
        """Execute QueryExecutionPlan with total count and offset pagination."""
        sess, is_temp = await self._resolve_session(session)
        try:
            # Base query
            stmt = select(CustomerMemory)
            count_stmt = select(func.count(CustomerMemory.id))

            if plan.criterion is not None:
                stmt = stmt.where(plan.criterion)
                count_stmt = count_stmt.where(plan.criterion)

            # Total count
            count_res = await sess.execute(count_stmt)
            total = count_res.scalar_one() or 0

            # Order by
            if plan.sort_clauses:
                stmt = stmt.order_by(*plan.sort_clauses)
            else:
                stmt = stmt.order_by(desc(CustomerMemory.updated_at), desc(CustomerMemory.id))

            # Offset pagination
            if plan.offset_params:
                stmt = stmt.offset(plan.offset_params.offset).limit(plan.offset_params.page_size)

            res = await sess.execute(stmt)
            items = list(res.scalars().all())
            return items, total
        finally:
            if is_temp:
                await sess.close()

    async def execute_query_plan_cursor(
        self,
        plan: QueryExecutionPlan,
        expected_workspace_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], bool, Optional[str], Optional[str]]:
        """Execute QueryExecutionPlan with workspace-isolated keyset cursor pagination."""
        sess, is_temp = await self._resolve_session(session)
        try:
            limit = plan.cursor_params.limit if plan.cursor_params else 50
            cursor_token = plan.cursor_params.cursor if plan.cursor_params else None

            stmt = select(CustomerMemory)
            where_clauses = []
            if plan.criterion is not None:
                where_clauses.append(plan.criterion)

            # Keyset pagination condition
            if cursor_token:
                decoded = CursorCodec.decode_cursor(cursor_token, expected_workspace_id=expected_workspace_id)
                cursor_u = decoded["updated_at"]
                cursor_id = decoded["id"]

                # Seek before (updated_at < cursor_u) OR (updated_at == cursor_u AND id < cursor_id)
                keyset_clause = or_(
                    CustomerMemory.updated_at < cursor_u,
                    and_(
                        CustomerMemory.updated_at == cursor_u,
                        CustomerMemory.id < cursor_id,
                    ),
                )
                where_clauses.append(keyset_clause)

            if where_clauses:
                stmt = stmt.where(and_(*where_clauses))

            # Deterministic sorting for keyset
            stmt = stmt.order_by(desc(CustomerMemory.updated_at), desc(CustomerMemory.id)).limit(limit + 1)

            res = await sess.execute(stmt)
            rows = list(res.scalars().all())

            has_more = len(rows) > limit
            items = rows[:limit]

            next_cursor = None
            if has_more and items:
                last_item = items[-1]
                next_cursor = CursorCodec.encode_cursor(
                    updated_at=last_item.updated_at,
                    item_id=last_item.id,
                    workspace_id=last_item.workspace_id,
                )

            return items, has_more, next_cursor, None
        finally:
            if is_temp:
                await sess.close()

    async def aggregate_memory_statistics(
        self,
        workspace_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Aggregate memory distribution, versioning, and storage metrics."""
        sess, is_temp = await self._resolve_session(session)
        try:
            base_stmt = select(CustomerMemory)
            if workspace_id:
                base_stmt = base_stmt.where(CustomerMemory.workspace_id == workspace_id)

            res = await sess.execute(base_stmt)
            memories = list(res.scalars().all())

            total = len(memories)
            active_count = sum(1 for m in memories if m.lifecycle_status == "ACTIVE" and not m.is_deleted)
            archived_count = sum(1 for m in memories if m.lifecycle_status == "ARCHIVED")
            locked_count = sum(1 for m in memories if m.lifecycle_status == "LOCKED")
            deleted_count = sum(1 for m in memories if m.is_deleted)
            migrating_count = sum(1 for m in memories if m.lifecycle_status == "MIGRATING")

            total_versions = sum(m.version_number for m in memories)
            max_version = max((m.version_number for m in memories), default=1)
            avg_versions = (total_versions / total) if total > 0 else 1.0

            # Payload size estimation
            total_payload_bytes = 0
            city_counts: Dict[str, int] = {}
            tag_counts: Dict[str, int] = {}

            for m in memories:
                payload = m.memory_payload or {}
                payload_str = json.dumps(payload)
                total_payload_bytes += len(payload_str.encode("utf-8"))

                # City frequency
                loc = payload.get("personal_info", {}).get("location", {})
                if isinstance(loc, dict) and loc.get("city"):
                    city = str(loc["city"]).strip().title()
                    city_counts[city] = city_counts.get(city, 0) + 1

                # Tag frequency
                tags = payload.get("identity", {}).get("tags", [])
                if isinstance(tags, list):
                    for t in tags:
                        tag_norm = str(t).strip().lower()
                        tag_counts[tag_norm] = tag_counts.get(tag_norm, 0) + 1

            avg_payload_bytes = (total_payload_bytes / total) if total > 0 else 0.0

            # Sort top frequencies
            top_cities = dict(sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            top_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])

            # Lifecycle distribution map
            lifecycle_dist = {
                "ACTIVE": active_count,
                "ARCHIVED": archived_count,
                "LOCKED": locked_count,
                "DELETED": deleted_count,
                "MIGRATING": migrating_count,
            }

            return {
                "total_memories": total,
                "active_count": active_count,
                "archived_count": archived_count,
                "locked_count": locked_count,
                "deleted_count": deleted_count,
                "migrating_count": migrating_count,
                "avg_versions_per_memory": round(avg_versions, 2),
                "max_versions_count": max_version,
                "estimated_storage_bytes": total_payload_bytes,
                "avg_payload_bytes": round(avg_payload_bytes, 2),
                "lifecycle_distribution": lifecycle_dist,
                "top_cities": top_cities,
                "top_tags": top_tags,
                "growth_time_series": [],
            }
        finally:
            if is_temp:
                await sess.close()

    # ── Legacy & Sub-Entity Methods ───────────────────────────────────────────

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
        sess, is_temp = await self._resolve_session(session)
        try:
            conditions = [CustomerMemory.is_deleted == False]  # noqa: E712
            if workspace_id:
                conditions.append(CustomerMemory.workspace_id == workspace_id)
            if lifecycle_status:
                status_val = lifecycle_status.value if hasattr(lifecycle_status, "value") else str(lifecycle_status)
                conditions.append(CustomerMemory.lifecycle_status == status_val)
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
            count_res = await sess.execute(count_stmt)
            total = count_res.scalar_one() or 0

            data_stmt = (
                select(CustomerMemory)
                .where(and_(*conditions))
                .order_by(desc(CustomerMemory.updated_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            res = await sess.execute(data_stmt)
            items = list(res.scalars().all())
            return items, total
        finally:
            if is_temp:
                await sess.close()

    async def get_timeline(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_id: Optional[UUID] = kwargs.get("customer_id")
        category: Optional[MemoryTimelineCategory] = kwargs.get("category")
        event_type: Optional[str] = kwargs.get("event_type")
        importance: Optional[MemoryImportance] = kwargs.get("importance")
        start_time: Optional[datetime] = kwargs.get("start_time")
        end_time: Optional[datetime] = kwargs.get("end_time")
        page: int = kwargs.get("page", 1)
        page_size: int = kwargs.get("page_size", 50)
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_id = args[1]
            else:
                customer_id = args[0]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemoryTimelineEvent).where(
                CustomerMemoryTimelineEvent.customer_id == customer_id
            )
            if workspace_id:
                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryTimelineEvent.customer_id).where(CustomerMemory.workspace_id == workspace_id)
            if category:
                stmt = stmt.where(CustomerMemoryTimelineEvent.category == category)
            if event_type:
                stmt = stmt.where(CustomerMemoryTimelineEvent.event_type == event_type)
            if importance:
                stmt = stmt.where(CustomerMemoryTimelineEvent.importance == importance)
            if start_time:
                stmt = stmt.where(CustomerMemoryTimelineEvent.created_at >= start_time)
            if end_time:
                stmt = stmt.where(CustomerMemoryTimelineEvent.created_at <= end_time)

            count_stmt = select(func.count()).select_from(stmt.subquery())
            count_res = await sess.execute(count_stmt)
            total = count_res.scalar_one()

            stmt = stmt.order_by(desc(CustomerMemoryTimelineEvent.created_at)).offset((page - 1) * page_size).limit(page_size)
            res = await sess.execute(stmt)
            return list(res.scalars().all()), total
        finally:
            if is_temp:
                await sess.close()

    async def get_versions(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryVersion], int]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_id: Optional[UUID] = kwargs.get("customer_id")
        page: int = kwargs.get("page", 1)
        page_size: int = kwargs.get("page_size", 50)
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_id = args[1]
            else:
                customer_id = args[0]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemoryVersion).where(CustomerMemoryVersion.customer_id == customer_id)
            if workspace_id:
                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryVersion.customer_id).where(CustomerMemory.workspace_id == workspace_id)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            count_res = await sess.execute(count_stmt)
            total = count_res.scalar_one()

            stmt = stmt.order_by(desc(CustomerMemoryVersion.version_number)).offset((page - 1) * page_size).limit(page_size)
            res = await sess.execute(stmt)
            return list(res.scalars().all()), total
        finally:
            if is_temp:
                await sess.close()

    async def get_version_by_number(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[CustomerMemoryVersion]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_id: Optional[UUID] = kwargs.get("customer_id")
        version_number: Optional[int] = kwargs.get("version_number")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_id = args[1]
                if len(args) > 2:
                    version_number = args[2]
            else:
                customer_id = args[0]
                if len(args) > 1:
                    version_number = args[1]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(CustomerMemoryVersion).where(
                CustomerMemoryVersion.customer_id == customer_id,
                CustomerMemoryVersion.version_number == version_number,
            )
            if workspace_id:
                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryVersion.customer_id).where(CustomerMemory.workspace_id == workspace_id)
            res = await sess.execute(stmt)
            return res.scalar_one_or_none()
        finally:
            if is_temp:
                await sess.close()

    async def get_change_logs(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[List[MemoryChangeLog], int]:
        session: Optional[AsyncSession] = kwargs.get("session")
        customer_id: Optional[UUID] = kwargs.get("customer_id")
        version_number: Optional[int] = kwargs.get("version_number")
        workspace_id: Optional[UUID] = kwargs.get("workspace_id")
        field_path: Optional[str] = kwargs.get("field_path")
        page: int = kwargs.get("page", 1)
        page_size: int = kwargs.get("page_size", 100)

        if args:
            if isinstance(args[0], AsyncSession):
                session = args[0]
                if len(args) > 1:
                    customer_id = args[1]
                if len(args) > 2:
                    version_number = args[2]
                if len(args) > 3:
                    field_path = args[3]
            else:
                customer_id = args[0]
                if len(args) > 1:
                    version_number = args[1]
                if len(args) > 2:
                    field_path = args[2]

        sess, is_temp = await self._resolve_session(session)
        try:
            stmt = select(MemoryChangeLog).where(MemoryChangeLog.customer_id == customer_id)
            if workspace_id:
                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == MemoryChangeLog.customer_id).where(CustomerMemory.workspace_id == workspace_id)
            if version_number is not None:
                stmt = stmt.where(MemoryChangeLog.version_number == version_number)
            if field_path is not None:
                stmt = stmt.where(MemoryChangeLog.field_path.like(f"{field_path}%"))

            count_stmt = select(func.count()).select_from(stmt.subquery())
            count_res = await sess.execute(count_stmt)
            total = count_res.scalar_one()

            stmt = stmt.order_by(desc(MemoryChangeLog.created_at)).offset((page - 1) * page_size).limit(page_size)
            res = await sess.execute(stmt)
            return list(res.scalars().all()), total
        finally:
            if is_temp:
                await sess.close()



__all__ = [
    "SqlAlchemyMemoryReadRepository",
]
