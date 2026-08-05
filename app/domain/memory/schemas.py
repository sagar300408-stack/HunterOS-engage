"""
HunterOS Engage — Memory Domain Schemas (Pydantic V2)

Foundational memory data contracts for structured customer knowledge.
Decoupled from AI extraction and conversation parsing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.memory.models import (
    ChangeType,
    LifecycleStatus,
    MemoryImportance,
    MemoryTimelineCategory,
)


# ── Structured Memory Blocks ──────────────────────────────────────────────────

class LocationInfo(BaseModel):
    """Geographical location attributes."""
    model_config = ConfigDict(extra="allow")

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    address_line: Optional[str] = None


class IdentityBlock(BaseModel):
    """Customer identity attributes and external links."""
    model_config = ConfigDict(extra="allow")

    aliases: List[str] = Field(default_factory=list)
    external_identifiers: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    verified_identities: List[str] = Field(default_factory=list)


class PersonalInfoBlock(BaseModel):
    """Personal and demographic factual profile."""
    model_config = ConfigDict(extra="allow")

    full_name: Optional[str] = None
    preferred_name: Optional[str] = None
    demographics: Dict[str, Any] = Field(default_factory=dict)
    occupation: Optional[str] = None
    employer: Optional[str] = None
    location: LocationInfo = Field(default_factory=LocationInfo)
    language: Optional[str] = "en"
    timezone: Optional[str] = "UTC"
    life_stage: Optional[str] = None


class FinancialInfoBlock(BaseModel):
    """Financial parameters and purchasing constraints."""
    model_config = ConfigDict(extra="allow")

    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "INR"
    financing_type: Optional[str] = None  # e.g., "self_funded", "pre_approved_loan", "mortgage"
    purchasing_capacity: Optional[str] = None
    income_bracket: Optional[str] = None
    investment_horizon: Optional[str] = None


class PropertyInfoBlock(BaseModel):
    """Property specifications and requirements."""
    model_config = ConfigDict(extra="allow")

    property_types: List[str] = Field(default_factory=list)  # e.g., ["apartment", "villa"]
    preferred_locations: List[str] = Field(default_factory=list)
    size_requirements: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"bhk": [2, 3], "sqft_min": 1200}
    amenities: List[str] = Field(default_factory=list)
    purpose: Optional[str] = None  # "end_use", "investment", "rental_yield"
    readiness: Optional[str] = None  # "immediate", "under_construction", "ready_to_move"


class RelationshipInfoBlock(BaseModel):
    """Key stakeholders, family, and referral ties."""
    model_config = ConfigDict(extra="allow")

    key_decision_makers: List[str] = Field(default_factory=list)
    family_composition: Optional[str] = None
    influencers: List[str] = Field(default_factory=list)
    referral_source: Optional[str] = None
    agent_broker_affiliations: List[str] = Field(default_factory=list)


class CommunicationPreferencesBlock(BaseModel):
    """Customer interaction and channel preferences."""
    model_config = ConfigDict(extra="allow")

    preferred_channels: List[str] = Field(default_factory=lambda: ["whatsapp"])
    preferred_contact_times: List[str] = Field(default_factory=list)
    frequency_preference: Optional[str] = None
    tone_preference: Optional[str] = None
    opt_in_statuses: Dict[str, bool] = Field(default_factory=lambda: {"whatsapp": True})


class BehavioralAttributesBlock(BaseModel):
    """Observed customer behavioral facts (non-synthetic)."""
    model_config = ConfigDict(extra="allow")

    interaction_preferences: Dict[str, Any] = Field(default_factory=dict)
    objections_noted: List[str] = Field(default_factory=list)
    communication_style: Optional[str] = None
    channel_responsiveness: Dict[str, str] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class JourneySnapshotBlock(BaseModel):
    """Factual journey state and lifecycle milestones."""
    model_config = ConfigDict(extra="allow")

    current_stage: Optional[str] = "NEW"
    stage_entered_at: Optional[datetime] = None
    milestone_history: List[Dict[str, Any]] = Field(default_factory=list)
    next_expected_action: Optional[str] = None


class MemoryMetadataBlock(BaseModel):
    """Metadata tracking data provenance and verification."""
    model_config = ConfigDict(extra="allow")

    verification_status: str = "UNVERIFIED"  # "UNVERIFIED", "VERIFIED", "FLAGGED"
    last_verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    source: str = "system"
    schema_version: str = "1.0.0"


class MemoryPayloadSchema(BaseModel):
    """
    Canonical memory payload bundling all structured memory blocks.
    """
    model_config = ConfigDict(extra="allow")

    identity: IdentityBlock = Field(default_factory=IdentityBlock)
    personal_info: PersonalInfoBlock = Field(default_factory=PersonalInfoBlock)
    financial_info: FinancialInfoBlock = Field(default_factory=FinancialInfoBlock)
    property_info: PropertyInfoBlock = Field(default_factory=PropertyInfoBlock)
    relationship_info: RelationshipInfoBlock = Field(default_factory=RelationshipInfoBlock)
    communication_preferences: CommunicationPreferencesBlock = Field(default_factory=CommunicationPreferencesBlock)
    behavioral_attributes: BehavioralAttributesBlock = Field(default_factory=BehavioralAttributesBlock)
    journey_snapshot: JourneySnapshotBlock = Field(default_factory=JourneySnapshotBlock)
    metadata: MemoryMetadataBlock = Field(default_factory=MemoryMetadataBlock)


# ── Request Schemas ───────────────────────────────────────────────────────────

class CustomerMemoryCreateRequest(BaseModel):
    """Request payload to initialize customer memory."""
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    workspace_id: Optional[UUID] = None
    memory_payload: Optional[MemoryPayloadSchema] = Field(default_factory=MemoryPayloadSchema)
    source: str = Field(default="API")
    created_by: Optional[str] = None
    idempotency_key: Optional[str] = None


class CustomerMemoryUpdateRequest(BaseModel):
    """Request payload for partial updating memory fields (PATCH)."""
    model_config = ConfigDict(extra="allow")

    workspace_id: Optional[UUID] = None
    memory_payload: Optional[Dict[str, Any]] = None
    reason: Optional[str] = "Customer profile update"
    trigger: str = Field(default="manual_update")
    changed_module: str = Field(default="API")
    changed_by: Optional[str] = None
    expected_revision_id: Optional[str] = None
    expected_version: Optional[int] = None
    idempotency_key: Optional[str] = None


class CustomerMemoryReplaceRequest(BaseModel):
    """Request payload for complete memory replacement (PUT)."""
    model_config = ConfigDict(extra="allow")

    workspace_id: Optional[UUID] = None
    memory_payload: MemoryPayloadSchema
    reason: Optional[str] = "Customer profile full replacement"
    trigger: str = Field(default="manual_replacement")
    changed_module: str = Field(default="API")
    changed_by: Optional[str] = None
    expected_revision_id: Optional[str] = None
    expected_version: Optional[int] = None
    idempotency_key: Optional[str] = None


class CustomerMemoryStatusChangeRequest(BaseModel):
    """Request payload for transitioning lifecycle status."""
    target_status: LifecycleStatus
    reason: Optional[str] = None
    changed_by: Optional[str] = None
    idempotency_key: Optional[str] = None


class CustomerMemoryBulkCreateRequest(BaseModel):
    """Request for bulk initializing customer memories."""
    items: List[CustomerMemoryCreateRequest]


class CustomerMemoryBulkGetRequest(BaseModel):
    """Request for bulk fetching customer memories."""
    customer_ids: List[UUID]
    include_deleted: bool = False


class CustomerMemoryBulkUpdateItem(BaseModel):
    """Single item in bulk update request."""
    customer_id: UUID
    update_data: CustomerMemoryUpdateRequest


class CustomerMemoryBulkUpdateRequest(BaseModel):
    """Request for bulk updating customer memories."""
    items: List[CustomerMemoryBulkUpdateItem]


class MemoryTimelineFilterRequest(BaseModel):
    """Parameters for filtering timeline events."""
    category: Optional[MemoryTimelineCategory] = None
    event_type: Optional[str] = None
    importance: Optional[MemoryImportance] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class MemorySearchRequest(BaseModel):
    """Multi-criteria search request across memory records."""
    workspace_id: Optional[UUID] = None
    search_term: Optional[str] = None
    current_stage: Optional[str] = None
    tags: Optional[List[str]] = None
    location_city: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    property_types: Optional[List[str]] = None
    lifecycle_status: Optional[LifecycleStatus] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


# ── Response Schemas ──────────────────────────────────────────────────────────

class CustomerMemoryResponse(BaseModel):
    """Full customer memory response representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    workspace_id: Optional[UUID] = None
    memory_payload: Dict[str, Any]
    version_number: int
    revision_id: str
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    etag: Optional[str] = None


class CustomerMemoryVersionResponse(BaseModel):
    """Summary of a historical memory version (Aggregate Snapshot)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    memory_id: UUID
    version_number: int
    schema_version: str
    snapshot_hash: str
    reason: Optional[str] = None
    trigger: str
    created_by: Optional[str] = None
    created_at: datetime


class CustomerMemoryVersionDetailResponse(CustomerMemoryVersionResponse):
    """Detailed memory version including full frozen snapshot data."""
    snapshot_data: Dict[str, Any]


class CustomerMemoryTimelineEventResponse(BaseModel):
    """Timeline event representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    memory_id: UUID
    category: MemoryTimelineCategory
    event_type: str
    title: str
    description: Optional[str] = None
    source: str
    importance: MemoryImportance
    payload: Optional[Dict[str, Any]] = None
    version_number: int
    created_at: datetime


class MemoryTimelineListResponse(BaseModel):
    """Paginated list of timeline events."""
    items: List[CustomerMemoryTimelineEventResponse]
    total: int
    page: int
    page_size: int


class MemoryChangeLogResponse(BaseModel):
    """Granular field-level change log record."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    memory_id: UUID
    version_number: int
    field_path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_type: ChangeType
    changed_module: str
    changed_by: Optional[str] = None
    created_at: datetime


class MemoryChangeLogListResponse(BaseModel):
    """Paginated list of change log records."""
    items: List[MemoryChangeLogResponse]
    total: int
    page: int
    page_size: int


class CustomerMemoryHistoryResponse(BaseModel):
    """
    Unified memory history representation combining memory state,
    chronological timeline, version snapshots, and field-level change logs.
    """
    memory: Optional[CustomerMemoryResponse] = None
    timeline: List[CustomerMemoryTimelineEventResponse] = Field(default_factory=list)
    versions: List[CustomerMemoryVersionResponse] = Field(default_factory=list)
    change_logs: List[MemoryChangeLogResponse] = Field(default_factory=list)


class CustomerMemorySearchResultItem(BaseModel):
    """Single search result entry."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    workspace_id: Optional[UUID] = None
    version_number: int
    revision_id: str
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    memory_payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CustomerMemorySearchResponse(BaseModel):
    """Paginated search response."""
    items: List[CustomerMemorySearchResultItem]
    total: int
    page: int
    page_size: int


class MemoryCursorSearchRequest(BaseModel):
    """Cursor-paginated search request across customer memories."""
    workspace_id: Optional[UUID] = None
    search_term: Optional[str] = None
    tags: Optional[List[str]] = None
    location_city: Optional[str] = None
    current_stage: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    lifecycle_status: Optional[str] = None
    cursor: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)


class MemoryCursorSearchResponse(BaseModel):
    """Keyset cursor-paginated search response."""
    items: List[CustomerMemorySearchResultItem]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool
    limit: int


class MemoryProjectionRequest(BaseModel):
    """Projection query request."""
    view_name: Optional[str] = None
    projection_mask: Optional[List[str]] = None
    projection_version: str = "1.0.0"
    bypass_cache: bool = False


class MemoryExportPreviewRequest(BaseModel):
    """Tabular export preview request."""
    workspace_id: Optional[UUID] = None
    export_format: str = "CSV"
    columns: Optional[List[str]] = None
    max_rows: int = Field(default=100, ge=1, le=1000)

