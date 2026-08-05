"""
HunterOS Engage — Context & Intelligence Integration Schemas (Phase 2.1.5)

Defines Pydantic DTOs for requests, responses, completeness, metadata, lineage,
and export formats including StructuredContextDTO.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.domain.memory.intelligence.models import (
    ContextBlockType,
    ContextCompletenessStatus,
    ContextScope,
    ExportTargetFormat,
)


# ── Metadata & Lineage Responses ─────────────────────────────────────────────

class ContextMetadataResponse(BaseModel):
    """Metadata response for composed context."""
    model_config = ConfigDict(populate_by_name=True)

    context_id: uuid.UUID
    context_version: int = 1
    generated_at: datetime
    schema_version: str = "1.0.0"
    source_modules: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    workspace_id: Optional[uuid.UUID] = None


class ContextLineageResponse(BaseModel):
    """Lineage response detailing provenance IDs."""
    model_config = ConfigDict(populate_by_name=True)

    source_memory_ids: List[str] = Field(default_factory=list)
    source_relationship_ids: List[str] = Field(default_factory=list)
    source_timeline_event_ids: List[str] = Field(default_factory=list)
    projections_applied: List[str] = Field(default_factory=list)
    generated_at: datetime
    source_modules: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ContextCompletenessResponse(BaseModel):
    """Completeness and quality diagnostic report."""
    model_config = ConfigDict(populate_by_name=True)

    score: float
    status: ContextCompletenessStatus
    total_blocks_requested: int
    blocks_loaded: int
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    is_valid: bool = True


# ── Request Options ──────────────────────────────────────────────────────────

class ContextRequestOptions(BaseModel):
    """Options for context composition and querying."""
    model_config = ConfigDict(populate_by_name=True)

    blocks: Optional[List[str]] = None
    max_graph_depth: int = Field(default=2, ge=1, le=5)
    include_timeline: bool = True
    include_versions: bool = False
    include_statistics: bool = True
    include_projections: bool = True
    relationship_types: Optional[List[str]] = None
    format: Optional[ExportTargetFormat] = None


class CustomContextRequest(BaseModel):
    """Request payload for custom arbitrary entity context composition."""
    model_config = ConfigDict(populate_by_name=True)

    entity_type: str
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    blocks: Optional[List[str]] = None
    max_graph_depth: int = Field(default=2, ge=1, le=5)
    format: Optional[ExportTargetFormat] = None


# ── Scope Context Responses ──────────────────────────────────────────────────

class CustomerContextResponse(BaseModel):
    """Standard API response for Customer 360 Context."""
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str
    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    memory: Optional[Dict[str, Any]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    versions: Optional[List[Dict[str, Any]]] = None
    projections: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None


class OrganizationContextResponse(BaseModel):
    """Standard API response for Organization Context."""
    model_config = ConfigDict(populate_by_name=True)

    organization_id: str
    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    relationships: Optional[List[Dict[str, Any]]] = None
    projections: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None


class OpportunityContextResponse(BaseModel):
    """Standard API response for Opportunity Context."""
    model_config = ConfigDict(populate_by_name=True)

    opportunity_id: str
    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    relationships: Optional[List[Dict[str, Any]]] = None
    projections: Optional[Dict[str, Any]] = None
    timeline: Optional[List[Dict[str, Any]]] = None


class PropertyContextResponse(BaseModel):
    """Standard API response for Property Context."""
    model_config = ConfigDict(populate_by_name=True)

    property_id: str
    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    relationships: Optional[List[Dict[str, Any]]] = None
    projections: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None


class ExecutiveContextResponse(BaseModel):
    """Standard API response for Executive Context."""
    model_config = ConfigDict(populate_by_name=True)

    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    statistics: Optional[Dict[str, Any]] = None
    projections: Optional[Dict[str, Any]] = None


class CustomContextResponse(BaseModel):
    """Standard API response for Custom Composed Context."""
    model_config = ConfigDict(populate_by_name=True)

    entity_type: str
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    metadata: ContextMetadataResponse
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
    blocks: Dict[str, Any] = Field(default_factory=dict)


# ── Export Models ────────────────────────────────────────────────────────────

class ExecutiveContextExportDTO(BaseModel):
    """High-level aggregated structural view for executive reporting."""
    model_config = ConfigDict(populate_by_name=True)

    scope: str
    entity_id: Optional[str] = None
    workspace_id: Optional[str] = None
    overview: Dict[str, Any] = Field(default_factory=dict)
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    highlights: List[str] = Field(default_factory=list)
    completeness_score: float = 1.0
    generated_at: datetime


class DashboardContextExportDTO(BaseModel):
    """Widget and card-ready structural views for frontend rendering."""
    model_config = ConfigDict(populate_by_name=True)

    scope: str
    entity_id: Optional[str] = None
    workspace_id: Optional[str] = None
    cards: List[Dict[str, Any]] = Field(default_factory=list)
    network_summary: Dict[str, Any] = Field(default_factory=dict)
    timeline_preview: List[Dict[str, Any]] = Field(default_factory=list)
    completeness: ContextCompletenessResponse


class StructuredContextDTO(BaseModel):
    """
    General-purpose structured context format consumable by AI prompts,
    external integrations, analytics, or UI dashboards without pre-baked inference.
    """
    model_config = ConfigDict(populate_by_name=True)

    context_id: uuid.UUID
    schema_version: str = "1.0.0"
    scope: str
    entity_key: str
    workspace_id: Optional[str] = None
    summary_sections: List[Dict[str, Any]] = Field(default_factory=list)
    entity_properties: Dict[str, Any] = Field(default_factory=dict)
    relationship_triplets: List[Dict[str, str]] = Field(default_factory=list)
    chronological_events: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    token_estimate: int = 0
    lineage: ContextLineageResponse
    completeness: ContextCompletenessResponse
