"""
HunterOS Engage V1 - Intent Intelligence Integration Domain Models
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Architectural Invariants:
1. Strict descriptive intent assembly across all 4 bounded contexts (Detection, Classification, Evolution, Resolution).
2. Zero predictive reasoning, no recommendations, no customer journey updates, no Memory modifications, no workflow executions.
3. Full relational graph traceability via IntentContextGraph (Detection -> Classification -> Evolution -> Resolution).
4. Deterministic CQRS role projections: Executive, Sales, Operations, Audit, Custom.
5. Zero-trust validation, strict workspace isolation, and complete provenance tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
import enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid
from pydantic import BaseModel, Field

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult


# ── 1. Enums ───────────────────────────────────────────────────────────────────

class CompositionProfileType(str, enum.Enum):
    """Supported declarative composition profiles."""
    MINIMAL = "MINIMAL"                   # Detection only
    CLASSIFICATION = "CLASSIFICATION"     # Classification only
    EVOLUTION = "EVOLUTION"               # Evolution only
    RESOLUTION = "RESOLUTION"             # Resolution only
    FULL = "FULL"                         # Complete 4-module intent context
    EXECUTIVE = "EXECUTIVE"               # Strategic & commercial focus
    SALES = "SALES"                       # Commercial intents, deal velocity, buying signals
    OPERATIONS = "OPERATIONS"             # Service/support requests, operational dependencies
    AUDIT = "AUDIT"                       # Exhaustive execution graph, rules fired, evidence IDs
    CUSTOM = "CUSTOM"                     # Caller-specified filtering criteria


class ContextGraphLinkType(str, enum.Enum):
    """Relational edge types across the unified IntentContextGraph."""
    CLASSIFIED_AS = "CLASSIFIED_AS"       # Detection -> Classification
    EVOLVED_INTO = "EVOLVED_INTO"         # Classification -> Evolution
    RESOLVED_IN = "RESOLVED_IN"           # Evolution/Classification -> Resolution Group
    DOMINATES = "DOMINATES"               # Dominant Intent -> Supporting Intent
    CONFLICTS_WITH = "CONFLICTS_WITH"     # Conflict Link
    DEPENDS_ON = "DEPENDS_ON"             # Dependency Link
    SUPPORTED_BY = "SUPPORTED_BY"         # Intent -> Message Evidence


# ── 2. Context Metadata & Provenance ──────────────────────────────────────────

class ContextMetadata(BaseModel):
    """Metadata describing the generated Intent Intelligence Context."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    workspace_id: str
    schema_version: str = "1.0.0"
    context_version: str = "1.0.0"
    composition_profile: str = CompositionProfileType.FULL.value
    source_modules: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextProvenance(BaseModel):
    """Deterministic provenance tracking for reproducibility and auditing."""
    integration_version: str = "1.0.0"
    gateway_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"
    engine_version: str = "1.0.0"
    composition_profile: str = CompositionProfileType.FULL.value
    source_modules: List[str] = Field(default_factory=list)
    detection_provenance: Optional[Dict[str, Any]] = None
    classification_provenance: Optional[Dict[str, Any]] = None
    evolution_provenance: Optional[Dict[str, Any]] = None
    resolution_provenance: Optional[Dict[str, Any]] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextDiagnostics(BaseModel):
    """Detailed diagnostics recorded during context assembly and validation."""
    is_valid: bool = True
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    evaluation_timings_ms: Dict[str, float] = Field(default_factory=dict)
    total_duration_ms: float = 0.0
    artifacts_processed: int = 0
    rules_applied: List[str] = Field(default_factory=list)


# ── 3. Completeness & Analytics ───────────────────────────────────────────────

class ContextCompletenessReport(BaseModel):
    """Descriptive evaluation of intent intelligence artifact completeness."""
    has_detection: bool = False
    has_classification: bool = False
    has_evolution: bool = False
    has_resolution: bool = False
    has_conversation_analysis: bool = False
    has_timeline: bool = False
    has_insights: bool = False
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_modules: List[str] = Field(default_factory=list)
    total_detected_intents: int = 0
    total_classified_intents: int = 0
    total_evolution_histories: int = 0
    total_resolved_groups: int = 0
    total_conflicts: int = 0
    total_dependencies: int = 0


class IntentContextAnalytics(BaseModel):
    """Descriptive analytics summarizing the integrated context."""
    intent_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    module_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_modules: List[str] = Field(default_factory=list)
    composition_size_bytes: int = 0
    total_intent_count: int = 0
    resolved_group_count: int = 0
    unresolved_conflict_count: int = 0
    dominant_intents_count: int = 0
    assembly_time_ms: float = 0.0
    validation_summary: Dict[str, Any] = Field(default_factory=dict)


# ── 4. Traceable Relational Context Graph ──────────────────────────────────────

class ContextGraphNode(BaseModel):
    """Unified node in the cross-subsystem relational context graph."""
    node_id: str
    subsystem: str  # "DETECTION", "CLASSIFICATION", "EVOLUTION", "RESOLUTION"
    intent_name: str
    confidence: float = 1.0
    status: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)


class ContextGraphLink(BaseModel):
    """Bidirectional relational link connecting nodes across subsystems."""
    link_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_node_id: str
    target_node_id: str
    link_type: ContextGraphLinkType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentContextGraph(BaseModel):
    """
    Traceable unified graph connecting Detection -> Classification -> Evolution -> Resolution.
    Allows downstream consumers (Customer Journey, Recommendation, Executive) to navigate
    intent relationships without manually joining separate DTOs.
    """
    graph_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    nodes: Dict[str, ContextGraphNode] = Field(default_factory=dict)
    links: List[ContextGraphLink] = Field(default_factory=list)

    def add_node(self, node: ContextGraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: ContextGraphLinkType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.links.append(
            ContextGraphLink(
                source_node_id=source_id,
                target_node_id=target_id,
                link_type=link_type,
                metadata=metadata or {},
            )
        )

    def get_lineage(self, intent_id: str) -> List[ContextGraphNode]:
        """Navigate full lineage across subsystems for a specific intent identifier."""
        raw_id = str(intent_id)
        # Look up deterministic sequential subsystem chain: DET -> CLS -> EVO -> RES
        canonical_keys = [f"det_{raw_id}", f"cls_{raw_id}", f"evo_{raw_id}", f"res_{raw_id}"]
        results = [self.nodes[k] for k in canonical_keys if k in self.nodes]
        if results:
            return results

        # Fallback graph search for arbitrary node IDs
        visited: Set[str] = set()
        queue: List[str] = [raw_id]
        fallback_results: List[ContextGraphNode] = []
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if curr in self.nodes:
                fallback_results.append(self.nodes[curr])

            for link in self.links:
                if link.link_type in (
                    ContextGraphLinkType.CLASSIFIED_AS,
                    ContextGraphLinkType.EVOLVED_INTO,
                    ContextGraphLinkType.RESOLVED_IN,
                ):
                    if link.source_node_id == curr and link.target_node_id not in visited:
                        queue.append(link.target_node_id)
                    elif link.target_node_id == curr and link.source_node_id not in visited:
                        queue.append(link.source_node_id)
        return fallback_results

    def get_conflicts(self, intent_id: str) -> List[ContextGraphNode]:
        """Get all intent nodes that conflict with the given intent ID."""
        raw_id = str(intent_id)
        seed_ids = {
            raw_id,
            f"res_{raw_id}",
            f"det_{raw_id}",
            f"cls_{raw_id}",
            f"evo_{raw_id}",
        }
        target_ids: Set[str] = set()
        for link in self.links:
            if link.link_type == ContextGraphLinkType.CONFLICTS_WITH:
                if link.source_node_id in seed_ids:
                    target_ids.add(link.target_node_id)
                elif link.target_node_id in seed_ids:
                    target_ids.add(link.source_node_id)
        return [self.nodes[tid] for tid in target_ids if tid in self.nodes]

    def get_dependencies(self, intent_id: str) -> List[ContextGraphNode]:
        """Get prerequisite intent nodes the given intent depends on."""
        raw_id = str(intent_id)
        seed_ids = {
            raw_id,
            f"res_{raw_id}",
            f"det_{raw_id}",
            f"cls_{raw_id}",
            f"evo_{raw_id}",
        }
        target_ids: Set[str] = set()
        for link in self.links:
            if link.link_type == ContextGraphLinkType.DEPENDS_ON:
                if link.source_node_id in seed_ids:
                    target_ids.add(link.target_node_id)
        return [self.nodes[tid] for tid in target_ids if tid in self.nodes]


# ── 5. CQRS Role Context Views ────────────────────────────────────────────────

class ExecutiveIntentContext(BaseModel):
    """Strategic role view tailored for C-suite and leadership intelligence."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    strategic_focus: List[str] = Field(default_factory=list)
    dominant_intents: List[Dict[str, Any]] = Field(default_factory=list)
    commercial_intensity_score: float = 0.0
    strategic_friction_count: int = 0
    high_severity_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    executive_summary: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SalesIntentContext(BaseModel):
    """Deal-oriented role view tailored for account executives, sales reps, and deal desk."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    active_commercial_intents: List[Dict[str, Any]] = Field(default_factory=list)
    buying_signals: List[str] = Field(default_factory=list)
    deal_blockers: List[Dict[str, Any]] = Field(default_factory=list)
    churn_risk_signals: List[str] = Field(default_factory=list)
    buying_vs_churn_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_motion: Optional[str] = None
    velocity_state: Optional[str] = None
    recommended_context_cues: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OperationsIntentContext(BaseModel):
    """Execution-oriented role view tailored for support, fulfillment, and customer success."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    service_requests: List[Dict[str, Any]] = Field(default_factory=list)
    document_requests: List[Dict[str, Any]] = Field(default_factory=list)
    cancellation_requests: List[Dict[str, Any]] = Field(default_factory=list)
    execution_dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    blocking_prerequisites: List[Dict[str, Any]] = Field(default_factory=list)
    operational_friction_count: int = 0
    unresolved_dependencies_count: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditIntentContext(BaseModel):
    """Exhaustive governance and audit view with complete cross-pipeline traceability."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    workspace_id: str
    rules_fired_by_subsystem: Dict[str, List[str]] = Field(default_factory=dict)
    evidence_message_id_map: Dict[str, List[str]] = Field(default_factory=dict)
    provenance_chain: ContextProvenance
    graph_snapshot: Dict[str, Any] = Field(default_factory=dict)
    validation_status: Dict[str, Any] = Field(default_factory=dict)
    evaluation_timings_ms: Dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomIntentContext(BaseModel):
    """Caller-customized projection view with selective filtering criteria."""
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    filtered_intents: List[Dict[str, Any]] = Field(default_factory=list)
    filtered_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    filtered_dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── 6. Root Aggregate Entity ──────────────────────────────────────────────────

class IntentIntelligenceContext(BaseModel):
    """
    The Unified Root Aggregate of Intent Intelligence.
    Consolidates Detection, Classification, Evolution, and Multi-Intent Resolution
    into a single immutable, deterministic integration model.
    """
    context_id: Union[uuid.UUID, str] = Field(default_factory=uuid.uuid4)
    conversation_id: str
    entity_id: str
    workspace_id: Optional[Union[uuid.UUID, str]] = None

    # Integrated Subsystem Artifacts
    detection_result: Optional[IntentDetectionResult] = None
    classification_result: Optional[IntentClassificationResult] = None
    evolution_result: Optional[IntentEvolutionResult] = None
    resolution_result: Optional[MultiIntentResolutionResult] = None

    # Optional Conversation Context Ingestions
    conversation_analysis: Optional[Any] = None
    conversation_timeline: Optional[Any] = None
    conversation_insights: Optional[Any] = None

    # Relational Graph & Analytics
    context_graph: IntentContextGraph = Field(default_factory=IntentContextGraph)
    analytics: IntentContextAnalytics = Field(default_factory=IntentContextAnalytics)
    completeness_report: ContextCompletenessReport = Field(default_factory=ContextCompletenessReport)

    # Metadata, Provenance & Diagnostics
    metadata: ContextMetadata
    provenance: ContextProvenance
    diagnostics: ContextDiagnostics = Field(default_factory=ContextDiagnostics)

    # Deterministic CQRS Role Projections
    executive_view: Optional[ExecutiveIntentContext] = None
    sales_view: Optional[SalesIntentContext] = None
    operations_view: Optional[OperationsIntentContext] = None
    audit_view: Optional[AuditIntentContext] = None
    custom_view: Optional[CustomIntentContext] = None


ContextMetadata.model_rebuild()
ContextDiagnostics.model_rebuild()
ContextProvenance.model_rebuild()
ExecutiveIntentContext.model_rebuild()
SalesIntentContext.model_rebuild()
OperationsIntentContext.model_rebuild()
AuditIntentContext.model_rebuild()
CustomIntentContext.model_rebuild()
IntentIntelligenceContext.model_rebuild()
