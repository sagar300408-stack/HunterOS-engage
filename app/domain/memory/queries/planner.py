"""
HunterOS Engage — Memory Query Planner

Analyzes, optimizes, and compiles specifications, filter groups, and sorting rules
into an optimized execution plan before delegating to the read repository.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, and_

from app.domain.memory.queries.filters import FilterCompiler, FilterGroup
from app.domain.memory.queries.pagination import CursorPaginationParams, OffsetPaginationParams
from app.domain.memory.queries.sorting import SortCompiler, SortField
from app.domain.memory.queries.specifications import AndSpecification, Specification, TrueSpecification


class QueryExecutionPlan(BaseModel):
    """Immutable compiled query execution plan ready for repository execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    criterion: Optional[Any] = Field(None, description="Compiled SQLAlchemy binary expression")
    sort_clauses: List[Any] = Field(default_factory=list, description="Compiled order_by clauses")
    offset_params: Optional[OffsetPaginationParams] = None
    cursor_params: Optional[CursorPaginationParams] = None
    plan_complexity: str = "SIMPLE"


class QueryPlanner:
    """
    Analyzes specifications and filter conditions to produce an optimal database query plan.
    Simplifies redundant boolean branches and consolidates filters.
    """

    @classmethod
    def create_plan(
        cls,
        model_class: Any,
        specifications: Optional[List[Specification]] = None,
        filter_group: Optional[FilterGroup] = None,
        sort_by: Optional[List[SortField]] = None,
        offset_params: Optional[OffsetPaginationParams] = None,
        cursor_params: Optional[CursorPaginationParams] = None,
    ) -> QueryExecutionPlan:
        """Construct an optimized QueryExecutionPlan."""
        # 1. Optimize and combine specifications
        combined_spec = cls.optimize_specifications(specifications)
        spec_crit = combined_spec.to_sqlalchemy_criterion(model_class) if combined_spec else None

        # 2. Compile filter group
        filter_crit = FilterCompiler.compile_group(filter_group, model_class) if filter_group else None

        # 3. Merge criteria
        all_criteria = []
        if spec_crit is not None:
            all_criteria.append(spec_crit)
        if filter_crit is not None:
            all_criteria.append(filter_crit)

        final_criterion = None
        if len(all_criteria) == 1:
            final_criterion = all_criteria[0]
        elif len(all_criteria) > 1:
            final_criterion = and_(*all_criteria)

        # 4. Compile sort clauses
        sort_clauses = SortCompiler.compile_sorts(sort_by, model_class)

        # 5. Determine complexity
        complexity = "COMPOSITE" if (specifications and len(specifications) > 2) or (filter_group and len(filter_group.conditions) > 3) else "SIMPLE"

        return QueryExecutionPlan(
            criterion=final_criterion,
            sort_clauses=sort_clauses,
            offset_params=offset_params,
            cursor_params=cursor_params,
            plan_complexity=complexity,
        )

    @classmethod
    def optimize_specifications(cls, specs: Optional[List[Specification]]) -> Optional[Specification]:
        """Flatten and simplify specification list."""
        if not specs:
            return None

        # Filter out TrueSpecifications
        active_specs = [s for s in specs if not isinstance(s, TrueSpecification)]
        if not active_specs:
            return None
        if len(active_specs) == 1:
            return active_specs[0]

        return AndSpecification(*active_specs)


__all__ = [
    "QueryExecutionPlan",
    "QueryPlanner",
]
