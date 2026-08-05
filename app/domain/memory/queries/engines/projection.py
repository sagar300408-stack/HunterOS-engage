"""
HunterOS Engage — Memory Projection Engine & Registry

Provides extensible projection view definitions, field masking, dynamic block shaping,
and projection versioning (V1, V2, etc.) for executive dashboards and client views.
"""

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.memory.queries.models import (
    CustomerMemoryDTO,
    ExecutiveViewDTO,
    LightweightViewDTO,
    ProjectedMemoryDTO,
    SummaryViewDTO,
)


class ProjectionDefinition(BaseModel):
    """Configuration definition for a named projection view."""
    model_config = ConfigDict(frozen=True)

    name: str
    version: str = "1.0.0"
    description: str
    required_blocks: List[str] = Field(default_factory=list)
    field_paths: List[str] = Field(default_factory=list)


class ProjectionRegistry:
    """
    Extensible registry for registering and resolving named projection views.
    Enables Phase 3 Executive Dashboard extensions without modifying core engine logic.
    """

    _registry: Dict[str, Dict[str, ProjectionDefinition]] = {}
    _transformers: Dict[str, Dict[str, Callable[[CustomerMemoryDTO, str], Any]]] = {}

    @classmethod
    def register_view(
        cls,
        definition: ProjectionDefinition,
        transformer: Optional[Callable[[CustomerMemoryDTO, str], Any]] = None,
    ) -> None:
        """Register a new view definition and optional custom DTO transformer."""
        name_key = definition.name.upper()
        version_key = definition.version
        cls._registry.setdefault(name_key, {})[version_key] = definition
        if transformer:
            cls._transformers.setdefault(name_key, {})[version_key] = transformer

    @classmethod
    def get_definition(cls, name: str, version: str = "1.0.0") -> Optional[ProjectionDefinition]:
        """Retrieve registered projection definition by name and version."""
        views_by_version = cls._registry.get(name.upper(), {})
        # Return exact version or latest available
        if version in views_by_version:
            return views_by_version[version]
        if views_by_version:
            return next(iter(views_by_version.values()))
        return None

    @classmethod
    def get_transformer(cls, name: str, version: str = "1.0.0") -> Optional[Callable[[CustomerMemoryDTO, str], Any]]:
        """Retrieve custom DTO transformer function if registered."""
        transformers_by_version = cls._transformers.get(name.upper(), {})
        if version in transformers_by_version:
            return transformers_by_version[version]
        if transformers_by_version:
            return next(iter(transformers_by_version.values()))
        return None


# ── Built-in Standard View Definitions ────────────────────────────────────────

def _transform_summary_view(dto: CustomerMemoryDTO, version: str) -> SummaryViewDTO:
    payload = dto.memory_payload or {}
    personal = payload.get("personal_info", {})
    identity = payload.get("identity", {})
    journey = payload.get("journey_snapshot", {})
    financial = payload.get("financial_info", {})

    return SummaryViewDTO(
        customer_id=dto.customer_id,
        workspace_id=dto.workspace_id,
        projection_version=version,
        full_name=personal.get("full_name"),
        city=personal.get("location", {}).get("city") if isinstance(personal.get("location"), dict) else None,
        lifecycle_status=dto.lifecycle_status,
        current_stage=journey.get("current_stage"),
        budget_max=financial.get("budget_max"),
        tags=list(identity.get("tags", [])),
        version_number=dto.version_number,
        updated_at=dto.updated_at,
    )


def _transform_executive_view(dto: CustomerMemoryDTO, version: str) -> ExecutiveViewDTO:
    payload = dto.memory_payload or {}
    personal = payload.get("personal_info", {})
    identity = payload.get("identity", {})
    journey = payload.get("journey_snapshot", {})
    financial = payload.get("financial_info", {})
    behavioral = payload.get("behavioral_attributes", {})

    # Determine financial capacity label
    budget_max = financial.get("budget_max")
    capacity = "UNKNOWN"
    if budget_max is not None:
        if budget_max >= 10000000:
            capacity = "ULTRA_HIGH_NET_WORTH"
        elif budget_max >= 5000000:
            capacity = "HIGH_NET_WORTH"
        elif budget_max >= 2000000:
            capacity = "AFFLUENT"
        else:
            capacity = "STANDARD"

    return ExecutiveViewDTO(
        customer_id=dto.customer_id,
        workspace_id=dto.workspace_id,
        projection_version=version,
        full_name=personal.get("full_name"),
        lifecycle_status=dto.lifecycle_status,
        financial_capacity=capacity,
        current_stage=journey.get("current_stage"),
        investment_intent=financial.get("investment_intent"),
        decision_makers=list(payload.get("relationship_info", {}).get("decision_makers", [])),
        top_tags=list(identity.get("tags", [])[:5]),
        timeline_events_count=len(journey.get("milestones", [])),
        version_number=dto.version_number,
        updated_at=dto.updated_at,
    )


def _transform_lightweight_view(dto: CustomerMemoryDTO, version: str) -> LightweightViewDTO:
    return LightweightViewDTO(
        customer_id=dto.customer_id,
        workspace_id=dto.workspace_id,
        projection_version=version,
        lifecycle_status=dto.lifecycle_status,
        version_number=dto.version_number,
        revision_id=dto.revision_id,
        updated_at=dto.updated_at,
    )


# Register standard views
ProjectionRegistry.register_view(
    ProjectionDefinition(
        name="SUMMARY",
        version="1.0.0",
        description="Fast search summary projection view",
        field_paths=["personal_info.full_name", "personal_info.location.city", "journey_snapshot.current_stage", "financial_info.budget_max", "identity.tags"],
    ),
    transformer=_transform_summary_view,
)

ProjectionRegistry.register_view(
    ProjectionDefinition(
        name="EXECUTIVE",
        version="1.0.0",
        description="Executive C-Suite strategic summary V1",
        field_paths=["personal_info.full_name", "financial_info", "journey_snapshot", "identity.tags"],
    ),
    transformer=_transform_executive_view,
)

ProjectionRegistry.register_view(
    ProjectionDefinition(
        name="EXECUTIVE",
        version="2.0.0",
        description="Executive C-Suite strategic summary V2",
        field_paths=["personal_info.full_name", "financial_info", "journey_snapshot", "identity.tags", "behavioral_attributes"],
    ),
    transformer=_transform_executive_view,
)

ProjectionRegistry.register_view(
    ProjectionDefinition(
        name="LIGHTWEIGHT",
        version="1.0.0",
        description="Ultra-lightweight edge sync projection",
        field_paths=["lifecycle_status", "version_number", "revision_id"],
    ),
    transformer=_transform_lightweight_view,
)


class MemoryProjectionEngine:
    """
    Projection Engine responsible for shaping customer memory records
    into versioned views, custom field masks, or structured DTOs.
    """

    @classmethod
    def project(
        cls,
        memory: CustomerMemoryDTO,
        view_name: Optional[str] = None,
        projection_mask: Optional[List[str]] = None,
        projection_version: str = "1.0.0",
    ) -> Any:
        """Project a customer memory record into the requested view or masked DTO."""
        if view_name:
            view_key = view_name.upper()
            transformer = ProjectionRegistry.get_transformer(view_key, projection_version)
            if transformer:
                return transformer(memory, projection_version)

        # Dynamic projection mask
        if projection_mask:
            projected_dict: Dict[str, Any] = {}
            for path in projection_mask:
                val = cls._extract_field(memory.memory_payload, path)
                if val is not None:
                    cls._set_nested(projected_dict, path, val)

            return ProjectedMemoryDTO(
                customer_id=memory.customer_id,
                projection_version=projection_version,
                view_name=view_name,
                lifecycle_status=memory.lifecycle_status,
                version_number=memory.version_number,
                updated_at=memory.updated_at,
                projected_data=projected_dict,
            )

        # Fallback: full projection DTO
        return ProjectedMemoryDTO(
            customer_id=memory.customer_id,
            projection_version=projection_version,
            view_name=view_name or "FULL",
            lifecycle_status=memory.lifecycle_status,
            version_number=memory.version_number,
            updated_at=memory.updated_at,
            projected_data=memory.memory_payload,
        )

    @classmethod
    def _extract_field(cls, payload: Dict[str, Any], path: str) -> Any:
        """Extract value by dot-notation path."""
        parts = path.split(".")
        curr: Any = payload
        for p in parts:
            if isinstance(curr, dict):
                curr = curr.get(p)
            else:
                return None
        return curr

    @classmethod
    def _set_nested(cls, root: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested dictionary value along dot-notation path."""
        parts = path.split(".")
        curr = root
        for i, p in enumerate(parts[:-1]):
            if p not in curr or not isinstance(curr[p], dict):
                curr[p] = {}
            curr = curr[p]
        curr[parts[-1]] = value


__all__ = [
    "ProjectionDefinition",
    "ProjectionRegistry",
    "MemoryProjectionEngine",
]
