"""
HunterOS Engage — Memory Search Engine

Unified search execution pipeline compiling specifications and filters,
optimizing execution via QueryPlanner, and coordinating repository reads.
"""

from typing import Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.filters import FilterCondition, FilterGroup, FilterOperator
from app.domain.memory.queries.models import (
    CustomerMemoryDTO,
    GetCursorPaginatedMemoryQuery,
    SearchCustomerMemoryQuery,
)
from app.domain.memory.queries.pagination import (
    CursorCodec,
    CursorPaginatedResult,
    CursorPaginationParams,
    OffsetPaginatedResult,
    OffsetPaginationParams,
)
from app.domain.memory.queries.planner import QueryPlanner
from app.domain.memory.queries.sorting import SortField
from app.domain.memory.queries.specifications import Specification, WorkspaceSpecification


class SearchCompiler:
    """
    Unified search compiler normalizing high-level search attributes
    (tags, locations, stages, budgets, text terms) into structured FilterGroups.
    """

    @classmethod
    def compile_search_params(
        cls,
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
    ) -> FilterGroup:
        """Combine all search criteria into a normalized FilterGroup."""
        conditions: List[Any] = []

        if workspace_id:
            conditions.append(FilterCondition(field="workspace_id", operator=FilterOperator.EQ, value=workspace_id))

        if lifecycle_status:
            conditions.append(FilterCondition(field="lifecycle_status", operator=FilterOperator.EQ, value=lifecycle_status.upper()))

        if location_city:
            conditions.append(FilterCondition(field="personal_info.location.city", operator=FilterOperator.ICONTAINS, value=location_city))

        if current_stage:
            conditions.append(FilterCondition(field="journey_snapshot.current_stage", operator=FilterOperator.EQ, value=current_stage))

        if min_budget is not None:
            conditions.append(FilterCondition(field="financial_info.budget_max", operator=FilterOperator.GTE, value=min_budget))

        if max_budget is not None:
            conditions.append(FilterCondition(field="financial_info.budget_min", operator=FilterOperator.LTE, value=max_budget))

        if tags:
            for tag in tags:
                conditions.append(FilterCondition(field="identity.tags", operator=FilterOperator.ICONTAINS, value=tag))

        if property_types:
            for p_type in property_types:
                conditions.append(FilterCondition(field="property_info.property_types", operator=FilterOperator.ICONTAINS, value=p_type))

        if search_term:
            # Match search term across full name, notes, or tags via OR group
            term_group = FilterGroup(
                logic="OR",
                conditions=[
                    FilterCondition(field="personal_info.full_name", operator=FilterOperator.ICONTAINS, value=search_term),
                    FilterCondition(field="identity.tags", operator=FilterOperator.ICONTAINS, value=search_term),
                    FilterCondition(field="personal_info.location.city", operator=FilterOperator.ICONTAINS, value=search_term),
                ],
            )
            conditions.append(term_group)

        if custom_filters and custom_filters.conditions:
            conditions.append(custom_filters)

        return FilterGroup(logic="AND", conditions=conditions)


class MemorySearchEngine:
    """
    Dedicated search engine executing offset and keyset cursor searches
    over customer memories without mutating domain state.
    """

    def __init__(self, repository: AbstractMemoryReadRepository) -> None:
        self._repo = repository

    async def search_offset(
        self,
        query: SearchCustomerMemoryQuery,
        session: Optional[AsyncSession] = None,
    ) -> OffsetPaginatedResult[CustomerMemoryDTO]:
        """Execute multi-criteria offset-paginated search."""
        offset_params = OffsetPaginationParams(page=query.page, page_size=query.page_size)

        specs = list(query.specifications or [])
        if query.workspace_id:
            specs.append(WorkspaceSpecification(query.workspace_id))

        plan = QueryPlanner.create_plan(
            model_class=self._repo.get_model_class(),
            specifications=specs,
            filter_group=query.filter_group,
            sort_by=query.sort_by,
            offset_params=offset_params,
        )

        entities, total = await self._repo.execute_query_plan_offset(plan, session=session)
        dtos = [self._to_dto(e) for e in entities]

        return OffsetPaginatedResult.create(
            items=dtos,
            total_count=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def search_cursor(
        self,
        query: GetCursorPaginatedMemoryQuery,
        session: Optional[AsyncSession] = None,
    ) -> CursorPaginatedResult[CustomerMemoryDTO]:
        """Execute keyset cursor-paginated search with workspace token protection."""
        cursor_params = CursorPaginationParams(cursor=query.cursor, limit=query.limit)

        specs = list(query.specifications or [])
        if query.workspace_id:
            specs.append(WorkspaceSpecification(query.workspace_id))

        plan = QueryPlanner.create_plan(
            model_class=self._repo.get_model_class(),
            specifications=specs,
            filter_group=query.filter_group,
            sort_by=query.sort_by,
            cursor_params=cursor_params,
        )

        entities, has_more, next_cursor, prev_cursor = await self._repo.execute_query_plan_cursor(
            plan=plan,
            expected_workspace_id=query.workspace_id,
            session=session,
        )
        dtos = [self._to_dto(e) for e in entities]

        return CursorPaginatedResult(
            items=dtos,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            limit=query.limit,
        )

    @staticmethod
    def _to_dto(entity: Any) -> CustomerMemoryDTO:
        """Convert repository aggregate or model to CustomerMemoryDTO."""
        if isinstance(entity, CustomerMemoryDTO):
            return entity
        return CustomerMemoryDTO(
            id=entity.id,
            customer_id=entity.customer_id,
            workspace_id=getattr(entity, "workspace_id", None),
            lifecycle_status=str(getattr(entity, "lifecycle_status", "ACTIVE")),
            version_number=getattr(entity, "version_number", 1),
            revision_id=str(getattr(entity, "revision_id", "")),
            is_deleted=bool(getattr(entity, "is_deleted", False)),
            deleted_at=getattr(entity, "deleted_at", None),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            memory_payload=dict(getattr(entity, "memory_payload", {}) or {}),
            schema_version=str(getattr(entity, "schema_version", "1.0.0")),
        )


__all__ = [
    "SearchCompiler",
    "MemorySearchEngine",
]
