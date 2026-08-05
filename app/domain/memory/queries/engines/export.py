"""
HunterOS Engage — Memory Export Engine

Transforms hierarchical CustomerMemory aggregates and payloads into flat,
tabular tabular rows ready for CSV, Excel, PDF, or external report generation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.models import (
    CustomerMemoryDTO,
    ExportPreviewQuery,
    MemoryExportColumn,
    MemoryExportDTO,
)
from app.domain.memory.queries.pagination import OffsetPaginationParams
from app.domain.memory.queries.planner import QueryPlanner
from app.domain.memory.queries.specifications import WorkspaceSpecification


class MemoryExportEngine:
    """
    Export Engine transforming complex JSON memory aggregates into
    standardized flat tabular representations.
    """

    DEFAULT_COLUMNS: List[MemoryExportColumn] = [
        MemoryExportColumn(key="customer_id", label="Customer ID", field_path="customer_id"),
        MemoryExportColumn(key="full_name", label="Full Name", field_path="personal_info.full_name"),
        MemoryExportColumn(key="city", label="City", field_path="personal_info.location.city"),
        MemoryExportColumn(key="lifecycle_status", label="Lifecycle Status", field_path="lifecycle_status"),
        MemoryExportColumn(key="current_stage", label="Current Stage", field_path="journey_snapshot.current_stage"),
        MemoryExportColumn(key="min_budget", label="Min Budget", field_path="financial_info.budget_min"),
        MemoryExportColumn(key="max_budget", label="Max Budget", field_path="financial_info.budget_max"),
        MemoryExportColumn(key="tags", label="Tags", field_path="identity.tags"),
        MemoryExportColumn(key="version_number", label="Version", field_path="version_number"),
        MemoryExportColumn(key="updated_at", label="Last Updated", field_path="updated_at"),
    ]

    def __init__(self, repository: AbstractMemoryReadRepository) -> None:
        self._repo = repository

    async def preview_export(
        self,
        query: ExportPreviewQuery,
        session: Optional[AsyncSession] = None,
    ) -> MemoryExportDTO:
        """Generate a tabular preview export dataset."""
        offset_params = OffsetPaginationParams(page=1, page_size=query.max_rows)

        specs = list(query.specifications or [])
        if query.workspace_id:
            specs.append(WorkspaceSpecification(query.workspace_id))

        plan = QueryPlanner.create_plan(
            model_class=self._repo.get_model_class(),
            specifications=specs,
            filter_group=query.filter_group,
            offset_params=offset_params,
        )

        entities, _ = await self._repo.execute_query_plan_offset(plan, session=session)

        # Determine active columns
        cols = self._resolve_columns(query.columns)
        col_headers = [c.label for c in cols]

        rows = []
        for e in entities:
            dto = self._to_dto(e)
            row_dict = {}
            for col in cols:
                val = self._extract_value(dto, col.field_path)
                # Format complex types (lists, datetimes)
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                elif isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col.label] = val
            rows.append(row_dict)

        return MemoryExportDTO(
            format=query.export_format.upper(),
            columns=col_headers,
            rows=rows,
            total_rows=len(rows),
            generated_at=datetime.now(timezone.utc),
        )

    def _resolve_columns(self, requested_keys: Optional[List[str]]) -> List[MemoryExportColumn]:
        """Resolve requested column list or fallback to defaults."""
        if not requested_keys:
            return self.DEFAULT_COLUMNS

        resolved = []
        lookup = {c.key.lower(): c for c in self.DEFAULT_COLUMNS}
        for k in requested_keys:
            k_lower = k.lower()
            if k_lower in lookup:
                resolved.append(lookup[k_lower])
            else:
                # Dynamic column from arbitrary JSON path
                resolved.append(MemoryExportColumn(key=k, label=k, field_path=k))
        return resolved or self.DEFAULT_COLUMNS

    def _extract_value(self, dto: CustomerMemoryDTO, field_path: str) -> Any:
        """Extract value from top-level DTO or deep memory payload."""
        if hasattr(dto, field_path):
            return getattr(dto, field_path)

        parts = field_path.split(".")
        curr: Any = dto.memory_payload or {}
        for p in parts:
            if isinstance(curr, dict):
                curr = curr.get(p)
            else:
                return None
        return curr

    @staticmethod
    def _to_dto(entity: Any) -> CustomerMemoryDTO:
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
    "MemoryExportEngine",
]
