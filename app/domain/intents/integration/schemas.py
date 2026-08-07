"""
HunterOS Engage V1 - Intent Intelligence Integration Schemas & DTOs
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Public API Contracts, Export DTOs, and CQRS Response Schemas.
Downstream modules must consume these DTOs exclusively.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.domain.intents.integration.models import CompositionProfileType


# ── 1. Metadata, Diagnostics & Provenance DTOs ────────────────────────────────

class ContextMetadataDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    workspace_id: str
    schema_version: str = "1.0.0"
    context_version: str = "1.0.0"
    composition_profile: str
    source_modules: List[str]
    created_at: datetime


class ContextProvenanceDTO(BaseModel):
    integration_version: str = "1.0.0"
    gateway_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"
    engine_version: str = "1.0.0"
    composition_profile: str
    source_modules: List[str]
    detection_provenance: Optional[Dict[str, Any]] = None
    classification_provenance: Optional[Dict[str, Any]] = None
    evolution_provenance: Optional[Dict[str, Any]] = None
    resolution_provenance: Optional[Dict[str, Any]] = None
    generated_at: datetime


class ContextDiagnosticsDTO(BaseModel):
    is_valid: bool
    warnings: List[str]
    validation_errors: List[str]
    evaluation_timings_ms: Dict[str, float]
    total_duration_ms: float
    artifacts_processed: int
    rules_applied: List[str]


class ContextCompletenessReportDTO(BaseModel):
    has_detection: bool
    has_classification: bool
    has_evolution: bool
    has_resolution: bool
    has_conversation_analysis: bool
    has_timeline: bool
    has_insights: bool
    completeness_score: float
    missing_modules: List[str]
    total_detected_intents: int
    total_classified_intents: int
    total_evolution_histories: int
    total_resolved_groups: int
    total_conflicts: int
    total_dependencies: int


class IntentContextAnalyticsDTO(BaseModel):
    intent_coverage: float
    module_coverage: float
    missing_modules: List[str]
    composition_size_bytes: int
    total_intent_count: int
    resolved_group_count: int
    unresolved_conflict_count: int
    dominant_intents_count: int
    assembly_time_ms: float
    validation_summary: Dict[str, Any]


# ── 2. Graph DTOs ─────────────────────────────────────────────────────────────

class ContextGraphNodeDTO(BaseModel):
    node_id: str
    subsystem: str
    intent_name: str
    confidence: float
    status: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)


class ContextGraphLinkDTO(BaseModel):
    link_id: uuid.UUID
    source_node_id: str
    target_node_id: str
    link_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentContextGraphDTO(BaseModel):
    graph_id: uuid.UUID
    node_count: int
    link_count: int
    nodes: Dict[str, ContextGraphNodeDTO]
    links: List[ContextGraphLinkDTO]


# ── 3. CQRS Context Role DTOs ─────────────────────────────────────────────────

class ExecutiveIntentContextDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    strategic_focus: List[str]
    dominant_intents: List[Dict[str, Any]]
    commercial_intensity_score: float
    strategic_friction_count: int
    high_severity_conflicts: List[Dict[str, Any]]
    executive_summary: str
    generated_at: datetime


class SalesIntentContextDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    active_commercial_intents: List[Dict[str, Any]]
    buying_signals: List[str]
    deal_blockers: List[Dict[str, Any]]
    churn_risk_signals: List[str]
    buying_vs_churn_conflicts: List[Dict[str, Any]]
    dominant_motion: Optional[str] = None
    velocity_state: Optional[str] = None
    recommended_context_cues: List[str]
    generated_at: datetime


class OperationsIntentContextDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    service_requests: List[Dict[str, Any]]
    document_requests: List[Dict[str, Any]]
    cancellation_requests: List[Dict[str, Any]]
    execution_dependencies: List[Dict[str, Any]]
    blocking_prerequisites: List[Dict[str, Any]]
    operational_friction_count: int
    unresolved_dependencies_count: int
    generated_at: datetime


class AuditIntentContextDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    workspace_id: str
    rules_fired_by_subsystem: Dict[str, List[str]]
    evidence_message_id_map: Dict[str, List[str]]
    provenance_chain: ContextProvenanceDTO
    graph_snapshot: Dict[str, Any]
    validation_status: Dict[str, Any]
    evaluation_timings_ms: Dict[str, float]
    generated_at: datetime


class CustomIntentContextDTO(BaseModel):
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    applied_filters: Dict[str, Any]
    filtered_intents: List[Dict[str, Any]]
    filtered_conflicts: List[Dict[str, Any]]
    filtered_dependencies: List[Dict[str, Any]]
    generated_at: datetime


# ── 4. Export Projection DTOs ─────────────────────────────────────────────────

class StandardAPIIntentContextDTO(BaseModel):
    """Clean API export schema for general REST integrations."""
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    workspace_id: str
    composition_profile: str
    detected_intents: List[Dict[str, Any]] = Field(default_factory=list)
    classified_intents: List[Dict[str, Any]] = Field(default_factory=list)
    intent_histories: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_groups: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    analytics: IntentContextAnalyticsDTO
    completeness: ContextCompletenessReportDTO
    metadata: ContextMetadataDTO
    provenance: ContextProvenanceDTO


class DashboardIntentContextDTO(BaseModel):
    """High-level aggregate payload for UI Dashboards and Command Centers."""
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    dominant_intents: List[Dict[str, Any]]
    total_intents_detected: int
    friction_count: int
    unresolved_blockers_count: int
    completeness_score: float
    buying_signals: List[str]
    risk_signals: List[str]
    executive_summary: str
    generated_at: datetime


class ExecutiveIntentDTO(BaseModel):
    """C-Suite condensed export schema."""
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    commercial_intensity: float
    primary_objectives: List[str]
    critical_risks: List[str]
    strategic_takeaway: str
    generated_at: datetime


class StructuredIntentContextDTO(BaseModel):
    """Structured hierarchical DTO optimized for downstream AI/LLM & Engine pipelines."""
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    intents_by_stage: Dict[str, List[Dict[str, Any]]]
    graph_representation: Dict[str, Any]
    active_conflicts: List[Dict[str, Any]]
    blocking_dependencies: List[Dict[str, Any]]
    dominance_rankings: List[Dict[str, Any]]
    completeness: ContextCompletenessReportDTO


# ── 5. Root Context DTO ───────────────────────────────────────────────────────

class IntentIntelligenceContextDTO(BaseModel):
    """Full unified context DTO representing complete Intent Intelligence."""
    context_id: uuid.UUID
    conversation_id: str
    entity_id: str
    workspace_id: str
    composition_profile: str
    metadata: ContextMetadataDTO
    provenance: ContextProvenanceDTO
    diagnostics: ContextDiagnosticsDTO
    completeness_report: ContextCompletenessReportDTO
    analytics: IntentContextAnalyticsDTO
    context_graph: IntentContextGraphDTO
    executive_view: Optional[ExecutiveIntentContextDTO] = None
    sales_view: Optional[SalesIntentContextDTO] = None
    operations_view: Optional[OperationsIntentContextDTO] = None
    audit_view: Optional[AuditIntentContextDTO] = None
    custom_view: Optional[CustomIntentContextDTO] = None


# ── 6. Request & Response Envelopes ───────────────────────────────────────────

class IntegrateIntentsRequest(BaseModel):
    """Request payload for Intent Integration Layer."""
    conversation_id: str
    entity_id: str
    workspace_id: str
    profile: CompositionProfileType = CompositionProfileType.FULL
    custom_filters: Optional[Dict[str, Any]] = None
    rule_packs: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None


class QueryIntentContextRequest(BaseModel):
    """Query payload for filtering and retrieving integration contexts."""
    conversation_id: Optional[str] = None
    entity_id: Optional[str] = None
    workspace_id: Optional[str] = None
    profile: Optional[CompositionProfileType] = None
    min_confidence: Optional[float] = None
    limit: int = 50
    offset: int = 0


class IntentIntelligenceResponse(BaseModel):
    """Standardized API response envelope for Intent Intelligence Platform."""
    success: bool = True
    context_id: uuid.UUID
    profile: str
    context: IntentIntelligenceContextDTO
    generated_at: datetime
