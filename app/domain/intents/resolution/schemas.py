"""
HunterOS Engage V1 - Multi-Intent Resolution DTO Schemas
Public contract DTOs, response models, request payloads, query filters, and analytics models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.resolution.models import (
    DominanceFactor,
    DominantIntent,
    GraphSnapshot,
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
    ResolutionDiagnostics,
    ResolutionMetadata,
    ResolutionProvenance,
    ResolutionStatus,
)


# ── Graph Public DTOs ────────────────────────────────────────────────────────

class IntentNodeDTO(BaseModel):
    """Public contract representation of an IntentNode."""
    model_config = ConfigDict(frozen=True)

    node_id: str
    intent_id: str
    canonical_name: str
    raw_intent_type: str = ""
    category: str = "GENERAL"
    taxonomy_path: str = ""
    confidence: float
    business_importance: str = "NORMAL"
    lifecycle_state: str = "ACTIVE"
    velocity: str = "STABLE"
    source_conversations: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    evidence_message_ids: List[str] = Field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, node: IntentNode) -> IntentNodeDTO:
        return cls(
            node_id=str(node.node_id),
            intent_id=str(node.intent_id),
            canonical_name=node.canonical_name,
            raw_intent_type=node.raw_intent_type,
            category=node.category,
            taxonomy_path=node.taxonomy_path,
            confidence=node.confidence,
            business_importance=node.business_importance,
            lifecycle_state=node.lifecycle_state,
            velocity=node.velocity,
            source_conversations=list(node.source_conversations),
            evidence_count=node.evidence_count,
            evidence_message_ids=list(node.evidence_message_ids),
            first_seen=node.first_seen,
            last_seen=node.last_seen,
            metadata=dict(node.metadata),
        )


class IntentRelationshipDTO(BaseModel):
    """Public contract representation of an IntentRelationship edge."""
    model_config = ConfigDict(frozen=True)

    relationship_id: str
    source_intent_id: str
    target_intent_id: str
    relationship_type: IntentRelationshipType
    strength: float = 1.0
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    rule_name: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @classmethod
    def from_domain(cls, rel: IntentRelationship) -> IntentRelationshipDTO:
        return cls(
            relationship_id=str(rel.relationship_id),
            source_intent_id=str(rel.source_intent_id),
            target_intent_id=str(rel.target_intent_id),
            relationship_type=rel.relationship_type,
            strength=rel.strength,
            evidence_ids=list(rel.evidence_ids),
            reason=rel.reason,
            rule_name=rel.rule_name,
            metadata=dict(rel.metadata),
            created_at=rel.created_at,
        )


class IntentConflictDTO(BaseModel):
    """Public contract representation of an IntentConflict."""
    model_config = ConfigDict(frozen=True)

    conflict_id: str
    conflict_type: IntentConflictType
    severity: IntentConflictSeverity
    intent_ids: List[str]
    description: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    resolution_hint: str = ""
    rule_name: str = ""
    detected_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, conflict: IntentConflict) -> IntentConflictDTO:
        return cls(
            conflict_id=str(conflict.conflict_id),
            conflict_type=conflict.conflict_type,
            severity=conflict.severity,
            intent_ids=[str(iid) for iid in conflict.intent_ids],
            description=conflict.description,
            evidence_ids=list(conflict.evidence_ids),
            resolution_hint=conflict.resolution_hint,
            rule_name=conflict.rule_name,
            detected_at=conflict.detected_at,
            metadata=dict(conflict.metadata),
        )


class IntentDependencyDTO(BaseModel):
    """Public contract representation of an IntentDependency."""
    model_config = ConfigDict(frozen=True)

    dependency_id: str
    dependency_type: IntentDependencyType
    source_intent_id: str
    target_intent_id: str
    is_blocking: bool = False
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    rule_name: str = ""
    detected_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, dep: IntentDependency) -> IntentDependencyDTO:
        return cls(
            dependency_id=str(dep.dependency_id),
            dependency_type=dep.dependency_type,
            source_intent_id=str(dep.source_intent_id),
            target_intent_id=str(dep.target_intent_id),
            is_blocking=dep.is_blocking,
            evidence_ids=list(dep.evidence_ids),
            reason=dep.reason,
            rule_name=dep.rule_name,
            detected_at=dep.detected_at,
            metadata=dict(dep.metadata),
        )


class DominantIntentDTO(BaseModel):
    """Public contract representation of a DominantIntent."""
    model_config = ConfigDict(frozen=True)

    intent_id: str
    canonical_name: str
    dominance_score: float
    primary_factor: Any = DominanceFactor.EVIDENCE_COVERAGE
    supporting_factors: Dict[str, float] = Field(default_factory=dict)
    factors: List[Any] = Field(default_factory=list)
    rationale: str = ""
    supporting_intent_ids: List[str] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, dom: DominantIntent) -> DominantIntentDTO:
        return cls(
            intent_id=str(dom.intent_id),
            canonical_name=dom.canonical_name,
            dominance_score=dom.dominance_score,
            primary_factor=dom.primary_factor,
            supporting_factors=dict(dom.supporting_factors),
            factors=getattr(dom, "factors", []),
            rationale=dom.rationale,
            supporting_intent_ids=[str(iid) for iid in dom.supporting_intent_ids],
        )


class IntentResolutionGraphDTO(BaseModel):
    """
    Public contract for IntentResolutionGraph outside the bounded context.
    Decouples internal graph representation from downstream consumers.
    """
    model_config = ConfigDict(frozen=True)

    graph_id: str
    nodes: Dict[str, IntentNodeDTO] = Field(default_factory=dict)
    edges: List[IntentRelationshipDTO] = Field(default_factory=list)
    conflicts: List[IntentConflictDTO] = Field(default_factory=list)
    dependencies: List[IntentDependencyDTO] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, graph: IntentResolutionGraph) -> IntentResolutionGraphDTO:
        return cls(
            graph_id=str(graph.graph_id),
            nodes={k: IntentNodeDTO.from_domain(v) for k, v in graph.nodes.items()},
            edges=[IntentRelationshipDTO.from_domain(e) for e in graph.edges],
            conflicts=[IntentConflictDTO.from_domain(c) for c in graph.conflicts],
            dependencies=[IntentDependencyDTO.from_domain(d) for d in graph.dependencies],
        )


class GraphSnapshotDTO(BaseModel):
    """Public DTO for GraphSnapshot."""
    model_config = ConfigDict(frozen=True)

    graph_snapshot_id: str
    graph_version: str
    node_count: int
    edge_count: int
    conflict_count: int
    dependency_count: int
    group_count: int
    dominant_intent_count: int
    captured_at: datetime

    @classmethod
    def from_domain(cls, snap: GraphSnapshot) -> GraphSnapshotDTO:
        return cls(
            graph_snapshot_id=str(snap.graph_snapshot_id),
            graph_version=snap.graph_version,
            node_count=snap.node_count,
            edge_count=snap.edge_count,
            conflict_count=snap.conflict_count,
            dependency_count=snap.dependency_count,
            group_count=snap.group_count,
            dominant_intent_count=snap.dominant_intent_count,
            captured_at=snap.captured_at,
        )


class IntentResolutionGroupDTO(BaseModel):
    """Public contract representation of an IntentResolutionGroup."""
    model_config = ConfigDict(frozen=True)

    group_id: str
    name: str
    group_type: str
    dominant_intent: Optional[DominantIntentDTO] = None
    supporting_intents: List[IntentNodeDTO] = Field(default_factory=list)
    all_intent_ids: List[str] = Field(default_factory=list)
    subgraph: Optional[IntentResolutionGraphDTO] = None
    conflicts: List[IntentConflictDTO] = Field(default_factory=list)
    dependencies: List[IntentDependencyDTO] = Field(default_factory=list)
    resolution_status: ResolutionStatus
    evidence_message_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, group: IntentResolutionGroup) -> IntentResolutionGroupDTO:
        return cls(
            group_id=str(group.group_id),
            name=group.name,
            group_type=group.group_type,
            dominant_intent=DominantIntentDTO.from_domain(group.dominant_intent) if group.dominant_intent else None,
            supporting_intents=[IntentNodeDTO.from_domain(si) for si in group.supporting_intents],
            all_intent_ids=[str(iid) for iid in group.all_intent_ids],
            subgraph=IntentResolutionGraphDTO.from_domain(group.subgraph) if group.subgraph else None,
            conflicts=[IntentConflictDTO.from_domain(c) for c in group.conflicts],
            dependencies=[IntentDependencyDTO.from_domain(d) for d in group.dependencies],
            resolution_status=group.resolution_status,
            evidence_message_ids=list(group.evidence_message_ids),
            metadata=dict(group.metadata),
        )


class ResolutionMetadataDTO(BaseModel):
    """Public DTO for ResolutionMetadata."""
    model_config = ConfigDict(frozen=True)

    entity_type: str
    entity_id: str
    workspace_id: Optional[str] = None
    conversation_id: str
    total_input_intents: int
    total_groups: int
    total_relationships: int
    total_conflicts: int
    total_dependencies: int
    total_dominant_intents: int
    evaluated_at: datetime

    @classmethod
    def from_domain(cls, meta: ResolutionMetadata) -> ResolutionMetadataDTO:
        return cls(
            entity_type=meta.entity_type,
            entity_id=meta.entity_id,
            workspace_id=str(meta.workspace_id) if meta.workspace_id else None,
            conversation_id=meta.conversation_id,
            total_input_intents=meta.total_input_intents,
            total_groups=meta.total_groups,
            total_relationships=meta.total_relationships,
            total_conflicts=meta.total_conflicts,
            total_dependencies=meta.total_dependencies,
            total_dominant_intents=meta.total_dominant_intents,
            evaluated_at=meta.evaluated_at,
        )


class ResolutionDiagnosticsDTO(BaseModel):
    """Public DTO for ResolutionDiagnostics."""
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float]
    stages_executed: List[str]
    rules_evaluated: int
    strategies_evaluated: int
    is_valid: bool
    validation_errors: List[str]
    warnings: List[str]

    @classmethod
    def from_domain(cls, diag: ResolutionDiagnostics) -> ResolutionDiagnosticsDTO:
        return cls(
            pipeline_execution_time_ms=diag.pipeline_execution_time_ms,
            stage_timings_ms=dict(diag.stage_timings_ms),
            stages_executed=list(diag.stages_executed),
            rules_evaluated=diag.rules_evaluated,
            strategies_evaluated=diag.strategies_evaluated,
            is_valid=diag.is_valid,
            validation_errors=list(diag.validation_errors),
            warnings=list(diag.warnings),
        )


class ResolutionProvenanceDTO(BaseModel):
    """Public DTO for ResolutionProvenance."""
    model_config = ConfigDict(frozen=True)

    resolution_version: str
    graph_version: str
    rule_pack_version: str
    pipeline_version: str
    engine_version: str
    rule_packs_applied: List[str]
    plugins_applied: List[str]
    generated_at: datetime

    @classmethod
    def from_domain(cls, prov: ResolutionProvenance) -> ResolutionProvenanceDTO:
        return cls(
            resolution_version=prov.resolution_version,
            graph_version=prov.graph_version,
            rule_pack_version=prov.rule_pack_version,
            pipeline_version=prov.pipeline_version,
            engine_version=prov.engine_version,
            rule_packs_applied=list(prov.rule_packs_applied),
            plugins_applied=list(prov.plugins_applied),
            generated_at=prov.generated_at,
        )


class IntentResolutionAnalyticsDTO(BaseModel):
    """
    Public DTO for Resolution Analytics metrics (User Directive 6).
    """
    model_config = ConfigDict(frozen=True)

    resolution_id: str
    graph_connectivity: float = Field(description="Ratio of edges to maximum possible edges (density)")
    relationship_density: float = Field(description="Edges per node")
    average_group_size: float = Field(description="Average number of intents per resolution group")
    conflict_frequency: float = Field(description="Ratio of conflicting intents to total intents")
    dependency_chains_count: int = Field(description="Count of active dependency links")
    intent_cohesion: float = Field(description="Clustering cohesion score across intent groups [0.0 - 1.0]")
    calculated_at: datetime


class MultiIntentResolutionResponse(BaseModel):
    """
    Top-level API response envelope for multi-intent resolution.
    """
    model_config = ConfigDict(frozen=True)

    resolution_id: str
    entity_type: str
    entity_id: str
    workspace_id: Optional[str] = None
    conversation_id: str
    resolution_graph: IntentResolutionGraphDTO
    groups: List[IntentResolutionGroupDTO]
    dominant_intents: List[DominantIntentDTO]
    snapshot: GraphSnapshotDTO
    metadata: ResolutionMetadataDTO
    diagnostics: ResolutionDiagnosticsDTO
    provenance: ResolutionProvenanceDTO
    analytics: Optional[IntentResolutionAnalyticsDTO] = None
    generated_at: datetime

    @classmethod
    def from_domain(cls, res: MultiIntentResolutionResult) -> MultiIntentResolutionResponse:
        # Calculate Analytics
        nodes_count = len(res.resolution_graph.nodes)
        edges_count = len(res.resolution_graph.edges)
        groups_count = len(res.groups)
        conflicts_count = len(res.resolution_graph.conflicts)
        deps_count = len(res.resolution_graph.dependencies)

        max_edges = (nodes_count * (nodes_count - 1)) / 2 if nodes_count > 1 else 1
        connectivity = min(1.0, float(edges_count) / float(max_edges)) if max_edges > 0 else 0.0
        density = float(edges_count) / float(nodes_count) if nodes_count > 0 else 0.0
        avg_group_size = float(nodes_count) / float(groups_count) if groups_count > 0 else 0.0
        conflict_freq = float(conflicts_count) / float(nodes_count) if nodes_count > 0 else 0.0
        cohesion = min(1.0, 0.5 + (0.5 * (1.0 - conflict_freq))) if nodes_count > 0 else 1.0

        analytics = IntentResolutionAnalyticsDTO(
            resolution_id=str(res.resolution_id),
            graph_connectivity=round(connectivity, 3),
            relationship_density=round(density, 3),
            average_group_size=round(avg_group_size, 2),
            conflict_frequency=round(conflict_freq, 3),
            dependency_chains_count=deps_count,
            intent_cohesion=round(cohesion, 3),
            calculated_at=res.generated_at,
        )

        return cls(
            resolution_id=str(res.resolution_id),
            entity_type=res.entity_type,
            entity_id=res.entity_id,
            workspace_id=str(res.workspace_id) if res.workspace_id else None,
            conversation_id=res.conversation_id,
            resolution_graph=IntentResolutionGraphDTO.from_domain(res.resolution_graph),
            groups=[IntentResolutionGroupDTO.from_domain(g) for g in res.groups],
            dominant_intents=[DominantIntentDTO.from_domain(d) for d in res.dominant_intents],
            snapshot=GraphSnapshotDTO.from_domain(res.snapshot),
            metadata=ResolutionMetadataDTO.from_domain(res.metadata),
            diagnostics=ResolutionDiagnosticsDTO.from_domain(res.diagnostics),
            provenance=ResolutionProvenanceDTO.from_domain(res.provenance),
            analytics=analytics,
            generated_at=res.generated_at,
        )


# ── Request Payloads & Query Filters ─────────────────────────────────────────

class ResolveIntentsRequest(BaseModel):
    """Request payload to trigger multi-intent resolution."""
    conversation_id: str
    customer_id: Optional[str] = None
    entity_type: str = "CUSTOMER"
    entity_id: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    rule_pack_names: Optional[List[str]] = None
    plugin_names: Optional[List[str]] = None
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)


class GroupFilterParams(BaseModel):
    """Query filters for intent resolution groups."""
    group_type: Optional[str] = None
    resolution_status: Optional[ResolutionStatus] = None
    has_conflicts: Optional[bool] = None
    has_dependencies: Optional[bool] = None
    has_dominant_intent: Optional[bool] = None


class RelationshipFilterParams(BaseModel):
    """Query filters for intent relationships."""
    relationship_type: Optional[IntentRelationshipType] = None
    source_intent_id: Optional[uuid.UUID] = None
    target_intent_id: Optional[uuid.UUID] = None
    min_strength: Optional[float] = None


class ConflictFilterParams(BaseModel):
    """Query filters for intent conflicts."""
    conflict_type: Optional[IntentConflictType] = None
    severity: Optional[IntentConflictSeverity] = None
    intent_id: Optional[uuid.UUID] = None


class DependencyFilterParams(BaseModel):
    """Query filters for intent dependencies."""
    dependency_type: Optional[IntentDependencyType] = None
    is_blocking: Optional[bool] = None
    source_intent_id: Optional[uuid.UUID] = None
    target_intent_id: Optional[uuid.UUID] = None
