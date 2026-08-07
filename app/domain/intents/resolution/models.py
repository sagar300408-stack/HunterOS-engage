"""
HunterOS Engage V1 - Multi-Intent Resolution Domain Models
Core entities, enums, graph structures, and aggregate root for multi-intent resolution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Set, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Enumerations ─────────────────────────────────────────────────────────────

class IntentRelationshipType(str, Enum):
    """Descriptive structural or contextual relationship between intents."""
    PARENT = "PARENT"
    CHILD = "CHILD"
    DOMINANT = "DOMINANT"
    SUPPORTING = "SUPPORTING"
    RELATED = "RELATED"
    COMPLEMENTARY = "COMPLEMENTARY"
    DEPENDENT = "DEPENDENT"
    CONFLICTING = "CONFLICTING"
    INDEPENDENT = "INDEPENDENT"
    CUSTOM = "CUSTOM"


class IntentConflictType(str, Enum):
    """Deterministic categorization of intent conflicts."""
    DUPLICATE = "DUPLICATE"
    CONTRADICTING = "CONTRADICTING"
    COMPETING = "COMPETING"
    MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"
    CLASSIFICATION_CONFLICT = "CLASSIFICATION_CONFLICT"
    TIMELINE_CONFLICT = "TIMELINE_CONFLICT"
    CUSTOM = "CUSTOM"


class IntentConflictSeverity(str, Enum):
    """Severity of a detected intent conflict."""
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntentDependencyType(str, Enum):
    """Type of observed business dependency between intents."""
    SEQUENTIAL = "SEQUENTIAL"
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    BLOCKING = "BLOCKING"
    BLOCKS = "BLOCKING"
    SUPPORTING = "SUPPORTING"
    CUSTOM = "CUSTOM"


class DominanceFactorType(str, Enum):
    """Deterministic factor contributing to intent dominance."""
    EVIDENCE_COVERAGE = "EVIDENCE_COVERAGE"
    CONVERSATION_FREQUENCY = "CONVERSATION_FREQUENCY"
    TIMELINE_PERSISTENCE = "TIMELINE_PERSISTENCE"
    CLASSIFICATION_CONSISTENCY = "CLASSIFICATION_CONSISTENCY"
    BUSINESS_IMPORTANCE = "BUSINESS_IMPORTANCE"
    COMMERCIAL_VALUE = "BUSINESS_IMPORTANCE"
    RULE_WEIGHTING = "RULE_WEIGHTING"


class DominanceFactor(BaseModel):
    """Dominance factor contributing detail."""
    model_config = ConfigDict(frozen=True)

    factor_type: Any = DominanceFactorType.EVIDENCE_COVERAGE
    score: float = 1.0
    rationale: str = ""

    EVIDENCE_COVERAGE: ClassVar[DominanceFactorType] = DominanceFactorType.EVIDENCE_COVERAGE
    CONVERSATION_FREQUENCY: ClassVar[DominanceFactorType] = DominanceFactorType.CONVERSATION_FREQUENCY
    TIMELINE_PERSISTENCE: ClassVar[DominanceFactorType] = DominanceFactorType.TIMELINE_PERSISTENCE
    CLASSIFICATION_CONSISTENCY: ClassVar[DominanceFactorType] = DominanceFactorType.CLASSIFICATION_CONSISTENCY
    BUSINESS_IMPORTANCE: ClassVar[DominanceFactorType] = DominanceFactorType.BUSINESS_IMPORTANCE
    COMMERCIAL_VALUE: ClassVar[DominanceFactorType] = DominanceFactorType.COMMERCIAL_VALUE
    RULE_WEIGHTING: ClassVar[DominanceFactorType] = DominanceFactorType.RULE_WEIGHTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_type": self.factor_type.value if hasattr(self.factor_type, "value") else str(self.factor_type),
            "score": self.score,
            "rationale": self.rationale,
        }


class IntentClusterType(str, Enum):
    """Clustering category for intent groups."""
    CO_OCCURRING = "CO_OCCURRING"
    TOPICAL = "TOPICAL"
    SEQUENTIAL = "SEQUENTIAL"
    CONFLICTING = "CONFLICTING"
    GENERAL = "GENERAL"


class ResolutionStatus(str, Enum):
    """Resolution state of an intent group or graph."""
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    INDEPENDENT = "INDEPENDENT"
    ACTIVE = "RESOLVED"


# ── Provenance & Snapshot ───────────────────────────────────────────────────

class ResolutionProvenance(BaseModel):
    """Complete version traceability metadata for resolution execution."""
    model_config = ConfigDict(frozen=True)

    resolution_version: str = "1.0.0"
    graph_version: str = "1.0.0"
    rule_pack_version: str = "1.0.0"
    pipeline_version: str = "2.3.4"
    engine_version: str = "1.0.0"
    rule_packs_applied: List[str] = Field(default_factory=list)
    plugins_applied: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_version": self.resolution_version,
            "graph_version": self.graph_version,
            "rule_pack_version": self.rule_pack_version,
            "pipeline_version": self.pipeline_version,
            "engine_version": self.engine_version,
            "rule_packs_applied": list(self.rule_packs_applied),
            "plugins_applied": list(self.plugins_applied),
            "generated_at": self.generated_at.isoformat(),
        }


class GraphSnapshot(BaseModel):
    """
    Point-in-time summary snapshot of the IntentResolutionGraph.
    Enables comparative analytics across time in downstream dashboards.
    """
    model_config = ConfigDict(frozen=True)

    graph_snapshot_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    graph_version: str = "1.0.0"
    node_count: int = 0
    edge_count: int = 0
    conflict_count: int = 0
    dependency_count: int = 0
    group_count: int = 0
    dominant_intent_count: int = 0
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_snapshot_id": str(self.graph_snapshot_id),
            "graph_version": self.graph_version,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "conflict_count": self.conflict_count,
            "dependency_count": self.dependency_count,
            "group_count": self.group_count,
            "dominant_intent_count": self.dominant_intent_count,
            "captured_at": self.captured_at.isoformat(),
        }


# ── Core Graph Entities ──────────────────────────────────────────────────────

class IntentNode(BaseModel):
    """
    Normalized node in the IntentResolutionGraph.
    Represents an intent enriched with metadata from Detection, Classification, and Evolution.
    """
    model_config = ConfigDict(frozen=True)

    node_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    intent_id: uuid.UUID
    canonical_name: str
    raw_intent_type: str = ""
    category: str = "GENERAL"
    taxonomy_path: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    business_importance: str = "NORMAL"
    lifecycle_state: str = "ACTIVE"
    velocity: str = "STABLE"
    source_conversations: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    evidence_message_ids: List[str] = Field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": str(self.node_id),
            "intent_id": str(self.intent_id),
            "canonical_name": self.canonical_name,
            "raw_intent_type": self.raw_intent_type,
            "category": self.category,
            "taxonomy_path": self.taxonomy_path,
            "confidence": self.confidence,
            "business_importance": self.business_importance,
            "lifecycle_state": self.lifecycle_state,
            "velocity": self.velocity,
            "source_conversations": list(self.source_conversations),
            "evidence_count": self.evidence_count,
            "evidence_message_ids": list(self.evidence_message_ids),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
        }


class IntentRelationship(BaseModel):
    """
    Descriptive relationship link (edge) between two intent nodes in the resolution graph.
    """
    model_config = ConfigDict(frozen=True)

    relationship_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_intent_id: uuid.UUID
    target_intent_id: uuid.UUID
    relationship_type: IntentRelationshipType
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    rule_name: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": str(self.relationship_id),
            "source_intent_id": str(self.source_intent_id),
            "target_intent_id": str(self.target_intent_id),
            "relationship_type": self.relationship_type.value,
            "strength": self.strength,
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "rule_name": self.rule_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class IntentConflict(BaseModel):
    """
    Evidence-based record of an observed conflict between two or more intents.
    """
    model_config = ConfigDict(frozen=True)

    conflict_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conflict_type: IntentConflictType
    severity: IntentConflictSeverity = IntentConflictSeverity.MEDIUM
    intent_ids: List[uuid.UUID] = Field(default_factory=list)
    description: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    resolution_hint: str = ""
    rule_name: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": str(self.conflict_id),
            "conflict_type": self.conflict_type.value,
            "severity": self.severity.value,
            "intent_ids": [str(i) for i in self.intent_ids],
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "resolution_hint": self.resolution_hint,
            "rule_name": self.rule_name,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


class IntentDependency(BaseModel):
    """
    Observed business dependency where source_intent is a prerequisite/upstream for target_intent.
    """
    model_config = ConfigDict(frozen=True)

    dependency_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    dependency_type: IntentDependencyType
    source_intent_id: uuid.UUID  # Prerequisite / Upstream
    target_intent_id: uuid.UUID  # Dependent / Downstream
    is_blocking: bool = False
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    rule_name: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency_id": str(self.dependency_id),
            "dependency_type": self.dependency_type.value,
            "source_intent_id": str(self.source_intent_id),
            "target_intent_id": str(self.target_intent_id),
            "is_blocking": self.is_blocking,
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "rule_name": self.rule_name,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


class DominantIntent(BaseModel):
    """
    Descriptive dominant intent record representing the central intent of a resolution group.
    """
    model_config = ConfigDict(frozen=True)

    intent_id: uuid.UUID
    canonical_name: str
    dominance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    primary_factor: Any = DominanceFactorType.EVIDENCE_COVERAGE
    supporting_factors: Dict[str, float] = Field(default_factory=dict)
    factors: List[DominanceFactor] = Field(default_factory=list)
    rationale: str = ""
    supporting_intent_ids: List[uuid.UUID] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": str(self.intent_id),
            "canonical_name": self.canonical_name,
            "dominance_score": self.dominance_score,
            "primary_factor": self.primary_factor.value if hasattr(self.primary_factor, "value") else str(self.primary_factor),
            "supporting_factors": dict(self.supporting_factors),
            "factors": [f.to_dict() if hasattr(f, "to_dict") else dict(f) for f in self.factors],
            "rationale": self.rationale,
            "supporting_intent_ids": [str(i) for i in self.supporting_intent_ids],
        }


class IntentResolutionGraph(BaseModel):
    """
    Complete resolution graph containing Nodes, Relationships, Conflicts, and Dependencies.
    """
    model_config = ConfigDict(frozen=True)

    graph_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    nodes: Dict[str, IntentNode] = Field(default_factory=dict)  # Keyed by str(intent_id)
    edges: List[IntentRelationship] = Field(default_factory=list)
    conflicts: List[IntentConflict] = Field(default_factory=list)
    dependencies: List[IntentDependency] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_node(self, intent_id: uuid.UUID) -> Optional[IntentNode]:
        return self.nodes.get(str(intent_id))

    def get_outgoing_relationships(self, intent_id: uuid.UUID) -> List[IntentRelationship]:
        return [e for e in self.edges if e.source_intent_id == intent_id]

    def get_incoming_relationships(self, intent_id: uuid.UUID) -> List[IntentRelationship]:
        return [e for e in self.edges if e.target_intent_id == intent_id]

    def get_conflicts_for_intent(self, intent_id: uuid.UUID) -> List[IntentConflict]:
        return [c for c in self.conflicts if intent_id in c.intent_ids]

    def get_dependencies_for_intent(self, intent_id: uuid.UUID) -> List[IntentDependency]:
        return [d for d in self.dependencies if d.source_intent_id == intent_id or d.target_intent_id == intent_id]

    def is_acyclic_dependencies(self) -> bool:
        """Verify that the dependency sub-graph contains no directed cycles."""
        adj: Dict[uuid.UUID, List[uuid.UUID]] = {}
        for d in self.dependencies:
            adj.setdefault(d.source_intent_id, []).append(d.target_intent_id)

        visited: Set[uuid.UUID] = set()
        rec_stack: Set[uuid.UUID] = set()

        def dfs(node: uuid.UUID) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if not dfs(neighbor):
                        return False
                elif neighbor in rec_stack:
                    return False
            rec_stack.remove(node)
            return True

        for n in adj:
            if n not in visited:
                if not dfs(n):
                    return False
        return True

    def create_snapshot(self, graph_version: str = "1.0.0", group_count: int = 0, dominant_count: int = 0) -> GraphSnapshot:
        return GraphSnapshot(
            graph_version=graph_version,
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            conflict_count=len(self.conflicts),
            dependency_count=len(self.dependencies),
            group_count=group_count,
            dominant_intent_count=dominant_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": str(self.graph_id),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "metadata": self.metadata,
        }


class IntentResolutionGroup(BaseModel):
    """
    Cohesive cluster of related intents with an identified dominant intent.
    """
    model_config = ConfigDict(frozen=True)

    group_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = ""
    group_type: str = "GENERAL"
    cluster_type: Any = IntentClusterType.GENERAL
    status: Any = ResolutionStatus.RESOLVED
    dominant_intent: Optional[DominantIntent] = None
    supporting_intents: List[IntentNode] = Field(default_factory=list)
    all_intent_ids: List[uuid.UUID] = Field(default_factory=list)
    subgraph: Optional[IntentResolutionGraph] = None
    conflicts: List[IntentConflict] = Field(default_factory=list)
    dependencies: List[IntentDependency] = Field(default_factory=list)
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    evidence_message_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": str(self.group_id),
            "name": self.name,
            "group_type": self.group_type,
            "cluster_type": self.cluster_type.value if hasattr(self.cluster_type, "value") else str(self.cluster_type),
            "dominant_intent": self.dominant_intent.to_dict() if self.dominant_intent else None,
            "supporting_intents": [s.to_dict() for s in self.supporting_intents],
            "all_intent_ids": [str(i) for i in self.all_intent_ids],
            "subgraph": self.subgraph.to_dict() if self.subgraph else None,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "resolution_status": self.resolution_status.value,
            "evidence_message_ids": list(self.evidence_message_ids),
            "metadata": self.metadata,
        }


# ── Metadata, Diagnostics & Aggregate Root ───────────────────────────────────

class ResolutionMetadata(BaseModel):
    """Execution summary statistics for multi-intent resolution."""
    model_config = ConfigDict(frozen=True)

    entity_type: str = "CUSTOMER"
    entity_id: str = ""
    workspace_id: Optional[uuid.UUID] = None
    conversation_id: str = ""
    total_input_intents: int = 0
    total_groups: int = 0
    total_relationships: int = 0
    total_conflicts: int = 0
    total_dependencies: int = 0
    dominant_intent_count: int = 0
    execution_duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_dominant_intents(self) -> int:
        return self.dominant_intent_count

    @property
    def evaluated_at(self) -> datetime:
        return self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "conversation_id": self.conversation_id,
            "total_input_intents": self.total_input_intents,
            "total_groups": self.total_groups,
            "total_relationships": self.total_relationships,
            "total_conflicts": self.total_conflicts,
            "total_dependencies": self.total_dependencies,
            "dominant_intent_count": self.dominant_intent_count,
            "execution_duration_ms": self.execution_duration_ms,
            "created_at": self.created_at.isoformat(),
        }


class ResolutionDiagnostics(BaseModel):
    """Diagnostic details of resolution pipeline stages."""
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float = 0.0
    stage_durations_ms: Dict[str, float] = Field(default_factory=dict)
    stages_executed: List[str] = Field(default_factory=list)
    applied_rules: List[str] = Field(default_factory=list)
    rules_evaluated: int = 0
    strategies_evaluated: int = 0
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def stage_timings_ms(self) -> Dict[str, float]:
        return self.stage_durations_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_execution_time_ms": self.pipeline_execution_time_ms,
            "stage_durations_ms": dict(self.stage_durations_ms),
            "stages_executed": list(self.stages_executed),
            "applied_rules": list(self.applied_rules),
            "rules_evaluated": self.rules_evaluated,
            "strategies_evaluated": self.strategies_evaluated,
            "is_valid": self.is_valid,
            "validation_errors": list(self.validation_errors),
            "warnings": list(self.warnings),
        }


class MultiIntentResolutionResult(BaseModel):
    """
    Immutable aggregate root emitted by the MultiIntentResolutionEngine.
    Official multi-intent resolution model artifact.
    """
    model_config = ConfigDict(frozen=True)

    resolution_id: Union[uuid.UUID, str] = Field(default_factory=uuid.uuid4)
    entity_type: str = "CUSTOMER"
    entity_id: str = ""
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    conversation_id: str = ""
    resolution_graph: IntentResolutionGraph = Field(default_factory=IntentResolutionGraph)
    groups: List[IntentResolutionGroup] = Field(default_factory=list)
    dominant_intents: List[DominantIntent] = Field(default_factory=list)
    snapshot: GraphSnapshot = Field(default_factory=GraphSnapshot)
    metadata: ResolutionMetadata = Field(default_factory=ResolutionMetadata)
    diagnostics: ResolutionDiagnostics = Field(default_factory=ResolutionDiagnostics)
    provenance: ResolutionProvenance = Field(default_factory=ResolutionProvenance)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "resolved_groups" in data and "groups" not in data:
                data["groups"] = data["resolved_groups"]
            elif "resolution_groups" in data and "groups" not in data:
                data["groups"] = data["resolution_groups"]
        return data

    @property
    def customer_id(self) -> Optional[str]:
        """Convenience accessor for customer workflows."""
        return self.entity_id if self.entity_type == "CUSTOMER" else None

    @property
    def resolved_groups(self) -> List[IntentResolutionGroup]:
        return self.groups

    @property
    def resolution_groups(self) -> List[IntentResolutionGroup]:
        return self.groups

    def get_group_by_id(self, group_id: uuid.UUID) -> Optional[IntentResolutionGroup]:
        for g in self.groups:
            if g.group_id == group_id:
                return g
        return None

    def get_group_for_intent(self, intent_id: uuid.UUID) -> Optional[IntentResolutionGroup]:
        for g in self.groups:
            if intent_id in g.all_intent_ids:
                return g
        return None

    def get_dominant_intent(self, group_id: uuid.UUID) -> Optional[DominantIntent]:
        group = self.get_group_by_id(group_id)
        return group.dominant_intent if group else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_id": str(self.resolution_id),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "conversation_id": self.conversation_id,
            "resolution_graph": self.resolution_graph.to_dict(),
            "groups": [g.to_dict() for g in self.groups],
            "dominant_intents": [d.to_dict() for d in self.dominant_intents],
            "snapshot": self.snapshot.to_dict(),
            "metadata": self.metadata.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "provenance": self.provenance.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }


# Aliases for cross-subsystem consistency
ResolutionSeverity = IntentConflictSeverity
ResolutionGroupStatus = ResolutionStatus
IntentGraphProvenance = ResolutionProvenance
IntentResolutionProvenance = ResolutionProvenance
IntentResolutionMetadata = ResolutionMetadata
IntentResolutionDiagnostics = ResolutionDiagnostics
IntentResolutionResult = MultiIntentResolutionResult

ResolutionProvenance.model_rebuild()
ResolutionMetadata.model_rebuild()
ResolutionDiagnostics.model_rebuild()
MultiIntentResolutionResult.model_rebuild()
