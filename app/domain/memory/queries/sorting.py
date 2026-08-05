"""
HunterOS Engage — Memory Query Sorting Engine

Provides dynamic sorting compilation across direct model columns and
nested JSON payload attributes with ascending/descending and nulls ordering support.
"""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, nulls_first, nulls_last, cast, Float, String


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class SortField(BaseModel):
    """Sort specification for a column or JSON path."""
    field: str = Field(description="Column name (e.g. 'updated_at') or JSON path (e.g. 'financial_info.budget_max')")
    direction: SortDirection = Field(default=SortDirection.ASC)
    nulls_first: Optional[bool] = Field(default=None, description="Explicit nulls positioning")


class SortCompiler:
    """Compiles SortField specifications into SQLAlchemy order_by clauses."""

    DIRECT_COLUMNS = {
        "id",
        "customer_id",
        "workspace_id",
        "lifecycle_status",
        "version_number",
        "revision_id",
        "is_deleted",
        "deleted_at",
        "created_at",
        "updated_at",
        "schema_version",
    }

    @classmethod
    def compile_sorts(cls, sort_fields: Optional[List[SortField]], model_class: Any) -> List[Any]:
        """Compile a list of SortField objects into SQLAlchemy ordering clauses."""
        if not sort_fields:
            # Default sort: updated_at DESC, id DESC
            return [desc(model_class.updated_at), desc(model_class.id)]

        clauses = []
        for sf in sort_fields:
            col_expr = cls._resolve_column(sf.field, model_class)
            if col_expr is None:
                continue

            order_fn = desc if sf.direction == SortDirection.DESC else asc
            order_clause = order_fn(col_expr)

            if sf.nulls_first is True:
                order_clause = nulls_first(order_clause)
            elif sf.nulls_first is False:
                order_clause = nulls_last(order_clause)

            clauses.append(order_clause)

        if not clauses:
            return [desc(model_class.updated_at), desc(model_class.id)]
        return clauses

    @classmethod
    def _resolve_column(cls, field_name: str, model_class: Any) -> Optional[Any]:
        """Resolve column or nested JSON path."""
        field_str = field_name.strip()
        if field_str in cls.DIRECT_COLUMNS:
            return getattr(model_class, field_str)

        # JSON payload path
        parts = field_str.split(".")
        try:
            expr = model_class.memory_payload
            for p in parts:
                expr = expr[p]
            return expr.astext
        except Exception:
            return None


__all__ = [
    "SortDirection",
    "SortField",
    "SortCompiler",
]
