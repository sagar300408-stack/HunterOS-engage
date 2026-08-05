"""
HunterOS Engage — Memory Query Filtering Engine

Provides comprehensive filtering capabilities across scalar columns and
deeply nested JSON payload fields with type coercion, null handling, and logical grouping.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import (
    BinaryExpression,
    ColumnElement,
    and_,
    cast,
    not_,
    or_,
    String,
    Float,
    Integer,
    Boolean,
)


class FilterOperator(str, Enum):
    """Supported filter operators for memory queries."""
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    ICONTAINS = "ICONTAINS"
    STARTS_WITH = "STARTS_WITH"
    BETWEEN = "BETWEEN"
    EXISTS = "EXISTS"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"


class FilterCondition(BaseModel):
    """Single filter condition applied to a column or nested JSON path."""
    field: str = Field(description="Column name or dot-notation JSON path (e.g. 'personal_info.location.city')")
    operator: FilterOperator = Field(default=FilterOperator.EQ)
    value: Optional[Any] = Field(default=None, description="Operand value or array of values for IN/BETWEEN")


class FilterGroup(BaseModel):
    """Group of filter conditions combined via AND / OR logical operators."""
    conditions: List[Union[FilterCondition, "FilterGroup"]] = Field(default_factory=list)
    logic: str = Field(default="AND", description="Logical combinator: 'AND' or 'OR'")


FilterGroup.model_rebuild()


class FilterCompiler:
    """Compiles FilterGroup and FilterCondition into SQLAlchemy expressions or evaluates in-memory."""

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
    def compile_group(cls, group: Optional[FilterGroup], model_class: Any) -> Optional[ColumnElement[bool]]:
        """Compile a FilterGroup into a composite SQLAlchemy expression."""
        if not group or not group.conditions:
            return None

        compiled_parts: List[ColumnElement[bool]] = []
        for item in group.conditions:
            if isinstance(item, FilterGroup):
                sub = cls.compile_group(item, model_class)
                if sub is not None:
                    compiled_parts.append(sub)
            elif isinstance(item, FilterCondition):
                crit = cls.compile_condition(item, model_class)
                if crit is not None:
                    compiled_parts.append(crit)

        if not compiled_parts:
            return None
        if len(compiled_parts) == 1:
            return compiled_parts[0]

        if group.logic.upper() == "OR":
            return or_(*compiled_parts)
        return and_(*compiled_parts)

    @classmethod
    def compile_condition(cls, cond: FilterCondition, model_class: Any) -> Optional[ColumnElement[bool]]:
        """Compile a single FilterCondition into a SQLAlchemy expression."""
        field_path = cond.field.strip()
        op = cond.operator
        val = cond.value

        # Direct model column
        if field_path in cls.DIRECT_COLUMNS:
            col = getattr(model_class, field_path)
            return cls._apply_operator(col, op, val)

        # JSON payload field extraction
        return cls._compile_json_field(model_class, field_path, op, val)

    @classmethod
    def _compile_json_field(cls, model_class: Any, field_path: str, op: FilterOperator, val: Any) -> Optional[ColumnElement[bool]]:
        """Extract and filter nested JSON field path on memory_payload."""
        parts = field_path.split(".")
        try:
            target_expr = model_class.memory_payload
            for p in parts:
                target_expr = target_expr[p]

            if op == FilterOperator.IS_NULL:
                return target_expr.is_(None)
            if op == FilterOperator.IS_NOT_NULL:
                return target_expr.is_not(None)

            # Type-aware extraction if value is numeric or boolean
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                num_col = cast(target_expr.astext, Float)
                return cls._apply_operator(num_col, op, float(val))
            elif isinstance(val, bool):
                bool_col = cast(target_expr.astext, Boolean)
                return cls._apply_operator(bool_col, op, val)
            else:
                str_col = target_expr.astext
                return cls._apply_operator(str_col, op, str(val) if val is not None else None)
        except Exception:
            # Fallback for SQLite / generic DB string match
            if val is not None:
                str_rep = str(val).lower()
                return cast(model_class.memory_payload, String).ilike(f"%{str_rep}%")
            return None

    @classmethod
    def _apply_operator(cls, col: Any, op: FilterOperator, val: Any) -> Optional[ColumnElement[bool]]:
        """Apply comparison operator to SQL column expression."""
        if op == FilterOperator.EQ:
            return col == val
        elif op == FilterOperator.NEQ:
            return col != val
        elif op == FilterOperator.GT:
            return col > val
        elif op == FilterOperator.GTE:
            return col >= val
        elif op == FilterOperator.LT:
            return col < val
        elif op == FilterOperator.LTE:
            return col <= val
        elif op == FilterOperator.IN:
            if isinstance(val, (list, tuple, set)):
                return col.in_(val)
            return col == val
        elif op == FilterOperator.NOT_IN:
            if isinstance(val, (list, tuple, set)):
                return col.not_in(val)
            return col != val
        elif op == FilterOperator.CONTAINS:
            return col.contains(str(val))
        elif op == FilterOperator.ICONTAINS:
            return col.ilike(f"%{val}%")
        elif op == FilterOperator.STARTS_WITH:
            return col.startswith(str(val))
        elif op == FilterOperator.BETWEEN:
            if isinstance(val, (list, tuple)) and len(val) == 2:
                return col.between(val[0], val[1])
            return None
        elif op == FilterOperator.IS_NULL:
            return col.is_(None)
        elif op == FilterOperator.IS_NOT_NULL:
            return col.is_not(None)
        elif op == FilterOperator.EXISTS:
            return col.is_not(None)
        return None

    @classmethod
    def evaluate_in_memory(cls, item: Dict[str, Any], group: FilterGroup) -> bool:
        """Evaluates FilterGroup against an in-memory dictionary representation."""
        if not group or not group.conditions:
            return True

        results: List[bool] = []
        for cond in group.conditions:
            if isinstance(cond, FilterGroup):
                results.append(cls.evaluate_in_memory(item, cond))
            elif isinstance(cond, FilterCondition):
                results.append(cls._eval_condition_dict(item, cond))

        if not results:
            return True
        if group.logic.upper() == "OR":
            return any(results)
        return all(results)

    @classmethod
    def _eval_condition_dict(cls, item: Dict[str, Any], cond: FilterCondition) -> bool:
        """Evaluate single condition against dictionary."""
        val = cls._get_nested_value(item, cond.field)
        op = cond.operator
        exp = cond.value

        if op == FilterOperator.EQ:
            return val == exp
        elif op == FilterOperator.NEQ:
            return val != exp
        elif op == FilterOperator.GT:
            return val > exp if val is not None and exp is not None else False
        elif op == FilterOperator.GTE:
            return val >= exp if val is not None and exp is not None else False
        elif op == FilterOperator.LT:
            return val < exp if val is not None and exp is not None else False
        elif op == FilterOperator.LTE:
            return val <= exp if val is not None and exp is not None else False
        elif op == FilterOperator.IN:
            return val in exp if isinstance(exp, (list, tuple, set)) else val == exp
        elif op == FilterOperator.NOT_IN:
            return val not in exp if isinstance(exp, (list, tuple, set)) else val != exp
        elif op == FilterOperator.CONTAINS:
            if isinstance(val, (list, tuple, set)):
                return exp in val
            return str(exp) in str(val) if val is not None else False
        elif op == FilterOperator.ICONTAINS:
            if isinstance(val, (list, tuple, set)):
                return any(str(exp).lower() in str(x).lower() for x in val)
            return str(exp).lower() in str(val).lower() if val is not None else False
        elif op == FilterOperator.STARTS_WITH:
            return str(val).startswith(str(exp)) if val is not None else False
        elif op == FilterOperator.BETWEEN:
            if isinstance(exp, (list, tuple)) and len(exp) == 2 and val is not None:
                return exp[0] <= val <= exp[1]
            return False
        elif op == FilterOperator.IS_NULL:
            return val is None
        elif op == FilterOperator.IS_NOT_NULL:
            return val is not None
        elif op == FilterOperator.EXISTS:
            return val is not None
        return False

    @staticmethod
    def _get_nested_value(item: Dict[str, Any], path: str) -> Any:
        """Extract dot-notated field value from dictionary."""
        if not path:
            return None
        parts = path.split(".")
        curr: Any = item
        # If payload is top-level or inside memory_payload
        if parts[0] not in item and "memory_payload" in item:
            curr = item["memory_payload"]

        for p in parts:
            if isinstance(curr, dict):
                curr = curr.get(p)
            else:
                return None
        return curr


__all__ = [
    "FilterOperator",
    "FilterCondition",
    "FilterGroup",
    "FilterCompiler",
]
