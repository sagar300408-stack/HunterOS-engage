"""
HunterOS Engage — Memory Query Specifications (Specification Pattern)

Provides composable, declarative specification classes supporting boolean
algebra (AND, OR, NOT) for querying customer memory models and payloads.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import BinaryExpression, and_, not_, or_
from sqlalchemy.sql.elements import ColumnElement


class Specification(ABC):
    """
    Abstract base specification.
    Supports composition via and_(), or_(), not_(), and Python operators (&, |, ~).
    """

    @abstractmethod
    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        """Translate specification into SQLAlchemy binary expression."""
        raise NotImplementedError

    @abstractmethod
    def is_satisfied_by(self, item: Any) -> bool:
        """Evaluate specification against in-memory dictionary or model instance."""
        raise NotImplementedError

    def and_(self, other: "Specification") -> "Specification":
        return AndSpecification(self, other)

    def or_(self, other: "Specification") -> "Specification":
        return OrSpecification(self, other)

    def not_(self) -> "Specification":
        return NotSpecification(self)

    def __and__(self, other: "Specification") -> "Specification":
        return self.and_(other)

    def __or__(self, other: "Specification") -> "Specification":
        return self.or_(other)

    def __invert__(self) -> "Specification":
        return self.not_()


class AndSpecification(Specification):
    """Composite AND specification."""

    def __init__(self, *specs: Specification) -> None:
        self.specs: List[Specification] = list(specs)

    def and_(self, other: Specification) -> "AndSpecification":
        return AndSpecification(*self.specs, other)

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        criteria = [s.to_sqlalchemy_criterion(model_class) for s in self.specs]
        valid_criteria = [c for c in criteria if c is not None]
        if not valid_criteria:
            return None
        if len(valid_criteria) == 1:
            return valid_criteria[0]
        return and_(*valid_criteria)

    def is_satisfied_by(self, item: Any) -> bool:
        return all(s.is_satisfied_by(item) for s in self.specs)


class OrSpecification(Specification):
    """Composite OR specification."""

    def __init__(self, *specs: Specification) -> None:
        self.specs: List[Specification] = list(specs)

    def or_(self, other: Specification) -> "OrSpecification":
        return OrSpecification(*self.specs, other)

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        criteria = [s.to_sqlalchemy_criterion(model_class) for s in self.specs]
        valid_criteria = [c for c in criteria if c is not None]
        if not valid_criteria:
            return None
        if len(valid_criteria) == 1:
            return valid_criteria[0]
        return or_(*valid_criteria)

    def is_satisfied_by(self, item: Any) -> bool:
        return any(s.is_satisfied_by(item) for s in self.specs)


class NotSpecification(Specification):
    """Negated NOT specification."""

    def __init__(self, spec: Specification) -> None:
        self.spec = spec

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        crit = self.spec.to_sqlalchemy_criterion(model_class)
        if crit is None:
            return None
        return not_(crit)

    def is_satisfied_by(self, item: Any) -> bool:
        return not self.spec.is_satisfied_by(item)


# ── Concrete Domain Specifications ────────────────────────────────────────────

class ActiveCustomersSpecification(Specification):
    """Matches active, non-deleted customer memory aggregates."""

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return and_(
            model_class.lifecycle_status == "ACTIVE",
            model_class.is_deleted == False,  # noqa: E712
        )

    def is_satisfied_by(self, item: Any) -> bool:
        status = getattr(item, "lifecycle_status", None) or (item.get("lifecycle_status") if isinstance(item, dict) else None)
        is_del = getattr(item, "is_deleted", False) or (item.get("is_deleted", False) if isinstance(item, dict) else False)
        return status == "ACTIVE" and not is_del


class ArchivedCustomersSpecification(Specification):
    """Matches customers in ARCHIVED lifecycle status."""

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.lifecycle_status == "ARCHIVED"

    def is_satisfied_by(self, item: Any) -> bool:
        status = getattr(item, "lifecycle_status", None) or (item.get("lifecycle_status") if isinstance(item, dict) else None)
        return status == "ARCHIVED"


class LockedCustomersSpecification(Specification):
    """Matches customers in LOCKED lifecycle status."""

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.lifecycle_status == "LOCKED"

    def is_satisfied_by(self, item: Any) -> bool:
        status = getattr(item, "lifecycle_status", None) or (item.get("lifecycle_status") if isinstance(item, dict) else None)
        return status == "LOCKED"


class WorkspaceSpecification(Specification):
    """Filters memory records by workspace tenant ID."""

    def __init__(self, workspace_id: UUID) -> None:
        self.workspace_id = workspace_id

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.workspace_id == self.workspace_id

    def is_satisfied_by(self, item: Any) -> bool:
        wid = getattr(item, "workspace_id", None) or (item.get("workspace_id") if isinstance(item, dict) else None)
        return str(wid) == str(self.workspace_id) if wid else False


class LifecycleSpecification(Specification):
    """Filters memory records by specific lifecycle status."""

    def __init__(self, status: str) -> None:
        self.status = status.upper()

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.lifecycle_status == self.status

    def is_satisfied_by(self, item: Any) -> bool:
        stat = getattr(item, "lifecycle_status", None) or (item.get("lifecycle_status") if isinstance(item, dict) else None)
        return stat == self.status if stat else False


class TagSpecification(Specification):
    """Filters memory records where identity tags array contains tag."""

    def __init__(self, tag: str) -> None:
        self.tag = tag.strip().lower()

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        # Works on PostgreSQL JSONB / SQLite JSON string extraction
        try:
            return model_class.memory_payload["identity"]["tags"].astext.contains(self.tag)
        except Exception:
            return model_class.memory_payload.cast(type_=Any).contains(self.tag)

    def is_satisfied_by(self, item: Any) -> bool:
        payload = getattr(item, "memory_payload", None) or (item.get("memory_payload") if isinstance(item, dict) else item)
        if isinstance(payload, dict):
            tags = payload.get("identity", {}).get("tags", [])
            return any(self.tag == str(t).strip().lower() for t in tags)
        return False


class LocationSpecification(Specification):
    """Filters memory records by city in personal info location."""

    def __init__(self, city: str) -> None:
        self.city = city.strip().lower()

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        try:
            return model_class.memory_payload["personal_info"]["location"]["city"].astext.ilike(f"%{self.city}%")
        except Exception:
            return model_class.memory_payload.cast(type_=Any).contains(self.city)

    def is_satisfied_by(self, item: Any) -> bool:
        payload = getattr(item, "memory_payload", None) or (item.get("memory_payload") if isinstance(item, dict) else item)
        if isinstance(payload, dict):
            loc_city = payload.get("personal_info", {}).get("location", {}).get("city", "")
            return self.city in str(loc_city).strip().lower()
        return False


class BudgetRangeSpecification(Specification):
    """Filters memory records where customer budget falls within [min_budget, max_budget]."""

    def __init__(self, min_budget: Optional[float] = None, max_budget: Optional[float] = None) -> None:
        self.min_budget = min_budget
        self.max_budget = max_budget

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        # In SQL, JSON payload filtering can be done via JSON extraction
        criteria = []
        if self.min_budget is not None:
            try:
                criteria.append(
                    model_class.memory_payload["financial_info"]["budget_max"].as_float() >= self.min_budget
                )
            except Exception:
                pass
        if self.max_budget is not None:
            try:
                criteria.append(
                    model_class.memory_payload["financial_info"]["budget_min"].as_float() <= self.max_budget
                )
            except Exception:
                pass
        return and_(*criteria) if criteria else None

    def is_satisfied_by(self, item: Any) -> bool:
        payload = getattr(item, "memory_payload", None) or (item.get("memory_payload") if isinstance(item, dict) else item)
        if isinstance(payload, dict):
            fin = payload.get("financial_info", {})
            b_min = fin.get("budget_min")
            b_max = fin.get("budget_max")
            if self.min_budget is not None and b_max is not None and float(b_max) < self.min_budget:
                return False
            if self.max_budget is not None and b_min is not None and float(b_min) > self.max_budget:
                return False
            return True
        return False


class UpdatedRecentlySpecification(Specification):
    """Filters memory records updated since cutoff timestamp."""

    def __init__(self, cutoff: datetime) -> None:
        self.cutoff = cutoff

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.updated_at >= self.cutoff

    def is_satisfied_by(self, item: Any) -> bool:
        updated = getattr(item, "updated_at", None) or (item.get("updated_at") if isinstance(item, dict) else None)
        return updated >= self.cutoff if updated else False


class VersionSpecification(Specification):
    """Filters memory records matching specific version number."""

    def __init__(self, version_number: int) -> None:
        self.version_number = version_number

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return model_class.version_number == self.version_number

    def is_satisfied_by(self, item: Any) -> bool:
        ver = getattr(item, "version_number", None) or (item.get("version_number") if isinstance(item, dict) else None)
        return ver == self.version_number


class TrueSpecification(Specification):
    """Specification that always evaluates to True."""

    def to_sqlalchemy_criterion(self, model_class: Any) -> Optional[ColumnElement[bool]]:
        return None

    def is_satisfied_by(self, item: Any) -> bool:
        return True


__all__ = [
    "Specification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    "ActiveCustomersSpecification",
    "ArchivedCustomersSpecification",
    "LockedCustomersSpecification",
    "WorkspaceSpecification",
    "LifecycleSpecification",
    "TagSpecification",
    "LocationSpecification",
    "BudgetRangeSpecification",
    "UpdatedRecentlySpecification",
    "VersionSpecification",
    "TrueSpecification",
]
