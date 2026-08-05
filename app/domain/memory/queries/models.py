"""
HunterOS Engage — Memory Query Objects & Immutable Read Model DTOs

Defines CQRS Query Objects and strictly immutable Read Model DTOs with
explicit projection versioning (V1, V2, etc.) for client compatibility.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


# ── Query Objects ─────────────────────────────────────────────────────────────

class BaseMemoryQuery(BaseModel):
    """Base query model providing traceability and cache policy."""
    model_config = ConfigDict(frozen=True)

    query_id: UUID = Field(default_factory=uuid4, description="Unique query execution correlation ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Query creation timestamp in UTC",
    )
    workspace_id: Optional[UUID] = Field(None, description="Optional tenant workspace scope")
    bypass_cache: bool = Field(False, description="Forces fresh read from repository bypassing query cache")


class GetCustomerMemoryQuery(BaseMemoryQuery):
    """Query to fetch a single customer's memory record."""
    customer_id: UUID
    include_deleted: bool = False
    include_locked: bool = True


class BulkGetCustomerMemoryQuery(BaseMemoryQuery):
    """Query to fetch multiple customer memory records by ID."""
    customer_ids: List[UUID]
    include_deleted: bool = False


class SearchCustomerMemoryQuery(BaseMemoryQuery):
    """Query for multi-criteria search with specifications, filters, sorting, and offset pagination."""
    filter_group: Optional[Any] = None
    specifications: Optional[List[Any]] = None
    sort_by: Optional[List[Any]] = None
    page: int = Field(1, ge=1, description="1-indexed page number")
    page_size: int = Field(50, ge=1, le=200, description="Items per page")


class GetCursorPaginatedMemoryQuery(BaseMemoryQuery):
    """Query for keyset cursor pagination with workspace isolation token."""
    filter_group: Optional[Any] = None
    specifications: Optional[List[Any]] = None
    sort_by: Optional[List[Any]] = None
    cursor: Optional[str] = Field(None, description="Base64-encoded workspace-isolated keyset token")
    limit: int = Field(50, ge=1, le=200, description="Max items to return")


class GetProjectionQuery(BaseMemoryQuery):
    """Query for projected or shaped memory view with versioning."""
    customer_id: UUID
    view_name: Optional[str] = Field(None, description="Named projection preset (SUMMARY, EXECUTIVE, etc.)")
    projection_mask: Optional[List[str]] = Field(None, description="List of dot-notation field paths")
    projection_version: str = Field("1.0.0", description="Requested projection schema version")


class GetStatisticsQuery(BaseMemoryQuery):
    """Query to aggregate business statistics and operational monitoring metrics."""
    include_operational_metrics: bool = True


class ExportPreviewQuery(BaseMemoryQuery):
    """Query to generate tabular export preview DTOs."""
    filter_group: Optional[Any] = None
    specifications: Optional[List[Any]] = None
    export_format: str = Field("CSV", description="Target export format (CSV, EXCEL, PDF, JSON)")
    columns: Optional[List[str]] = Field(None, description="Selected export column headers / field paths")
    max_rows: int = Field(100, ge=1, le=1000, description="Maximum rows to include in preview")


# ── Read Model DTOs (Strictly Frozen / Immutable) ─────────────────────────────

class CustomerMemoryDTO(BaseModel):
    """Immutable full read model representing current customer memory."""
    model_config = ConfigDict(frozen=True)

    id: UUID
    customer_id: UUID
    workspace_id: Optional[UUID] = None
    lifecycle_status: str
    version_number: int
    revision_id: str
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    memory_payload: Dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1.0.0"


class ProjectedMemoryDTO(BaseModel):
    """Dynamic projected memory read model supporting field masking and block slicing."""
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    projection_version: str = "1.0.0"
    view_name: Optional[str] = None
    lifecycle_status: str
    version_number: int
    updated_at: datetime
    projected_data: Dict[str, Any] = Field(default_factory=dict)


class SummaryViewDTO(BaseModel):
    """Standard summary view read model for fast list views and searches."""
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    workspace_id: Optional[UUID] = None
    projection_version: str = "1.0.0"
    full_name: Optional[str] = None
    city: Optional[str] = None
    lifecycle_status: str
    current_stage: Optional[str] = None
    budget_max: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    version_number: int
    updated_at: datetime


class ExecutiveViewDTO(BaseModel):
    """Executive C-suite view read model highlighting strategic customer capacity."""
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    workspace_id: Optional[UUID] = None
    projection_version: str = "1.0.0"
    full_name: Optional[str] = None
    lifecycle_status: str
    financial_capacity: Optional[str] = None
    current_stage: Optional[str] = None
    investment_intent: Optional[str] = None
    decision_makers: List[str] = Field(default_factory=list)
    top_tags: List[str] = Field(default_factory=list)
    timeline_events_count: int = 0
    version_number: int
    updated_at: datetime


class LightweightViewDTO(BaseModel):
    """Ultra-compact read model for edge/mobile sync and cache verification."""
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    workspace_id: Optional[UUID] = None
    projection_version: str = "1.0.0"
    lifecycle_status: str
    version_number: int
    revision_id: str
    updated_at: datetime


class OperationalMetricsDTO(BaseModel):
    """Operational query performance and telemetry read model."""
    model_config = ConfigDict(frozen=True)

    total_queries_executed: int = 0
    average_query_time_ms: float = 0.0
    slow_queries_count: int = 0
    cache_hit_ratio: float = 0.0
    repository_execution_time_ms: float = 0.0
    active_cache_entries: int = 0


class MemoryStatisticsDTO(BaseModel):
    """Domain and operational aggregate memory statistics read model."""
    model_config = ConfigDict(frozen=True)

    total_memories: int
    active_count: int
    archived_count: int
    locked_count: int
    deleted_count: int
    migrating_count: int
    avg_versions_per_memory: float
    max_versions_count: int
    estimated_storage_bytes: int
    avg_payload_bytes: float
    lifecycle_distribution: Dict[str, int]
    top_cities: Dict[str, int]
    top_tags: Dict[str, int]
    growth_time_series: List[Dict[str, Any]] = Field(default_factory=list)
    operational_metrics: Optional[OperationalMetricsDTO] = None


class MemoryExportColumn(BaseModel):
    """Export column definition."""
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    field_path: str


class MemoryExportDTO(BaseModel):
    """Tabular formatted export dataset ready for CSV, Excel, PDF, or JSON generation."""
    model_config = ConfigDict(frozen=True)

    format: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = [
    "BaseMemoryQuery",
    "GetCustomerMemoryQuery",
    "BulkGetCustomerMemoryQuery",
    "SearchCustomerMemoryQuery",
    "GetCursorPaginatedMemoryQuery",
    "GetProjectionQuery",
    "GetStatisticsQuery",
    "ExportPreviewQuery",
    "CustomerMemoryDTO",
    "ProjectedMemoryDTO",
    "SummaryViewDTO",
    "ExecutiveViewDTO",
    "LightweightViewDTO",
    "OperationalMetricsDTO",
    "MemoryStatisticsDTO",
    "MemoryExportColumn",
    "MemoryExportDTO",
]
