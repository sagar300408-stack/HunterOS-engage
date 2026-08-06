"""
HunterOS Engage V1 - Intent History & Evolution Domain Models
Core entities, lifecycle states, evolution event streams, timelines, and aggregates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    """Subject entity type for generalized multi-entity evolution."""
    CUSTOMER = "CUSTOMER"
    ORGANIZATION = "ORGANIZATION"
    DEAL = "DEAL"
    OPPORTUNITY = "OPPORTUNITY"
    PROJECT = "PROJECT"
    CUSTOM = "CUSTOM"


class IntentLifecycleState(str, Enum):
    """
    Descriptive lifecycle state for a customer/entity intent.
    Lifecycle states are strictly descriptive of observed evidence.
    """
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    PERSISTING = "PERSISTING"
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    CHANGED = "CHANGED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    RESOLVED = "RESOLVED"
    INACTIVE = "INACTIVE"
    CLOSED = "CLOSED"


class IntentEvolutionEventType(str, Enum):
    """Discrete evolution event types representing observable transitions."""
    INTENT_CREATED = "INTENT_CREATED"
    INTENT_UPDATED = "INTENT_UPDATED"
    INTENT_STRENGTH_INCREASED = "INTENT_STRENGTH_INCREASED"
    INTENT_STRENGTH_DECREASED = "INTENT_STRENGTH_DECREASED"
    INTENT_MERGED = "INTENT_MERGED"
    INTENT_SPLIT = "INTENT_SPLIT"
    INTENT_RECLASSIFIED = "INTENT_RECLASSIFIED"
    INTENT_RESOLVED = "INTENT_RESOLVED"
    INTENT_CLOSED = "INTENT_CLOSED"
    CUSTOM_EVOLUTION_EVENT = "CUSTOM_EVOLUTION_EVENT"


class IntentVelocity(str, Enum):
    """Historical rate of observation and reinforcement across conversations."""
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    SPORADIC = "SPORADIC"
    UNKNOWN = "UNKNOWN"


# ── Provenance & State Snapshot ──────────────────────────────────────────────

class EvolutionProvenance(BaseModel):
    """Audit provenance for evolution generation and execution telemetry."""
    model_config = ConfigDict(frozen=True)

    evolution_version: str = "1.0.0"
    strategy_version: str = "1.0.0"
    generator_version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evolution_version": self.evolution_version,
            "strategy_version": self.strategy_version,
            "generator_version": self.generator_version,
            "generated_at": self.generated_at.isoformat(),
        }


class IntentStateSnapshot(BaseModel):
    """
    Immutable state of an intent observed at a specific conversation and point in time.
    """
    model_config = ConfigDict(frozen=True)

    snapshot_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    intent_id: uuid.UUID
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    intent_type: str
    category: str
    taxonomy_path: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_message_ids: List[str] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": str(self.snapshot_id),
            "intent_id": str(self.intent_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "intent_type": self.intent_type,
            "category": self.category,
            "taxonomy_path": self.taxonomy_path,
            "confidence": self.confidence,
            "observed_at": self.observed_at.isoformat(),
            "evidence_message_ids": list(self.evidence_message_ids),
            "relationships": [dict(r) for r in self.relationships],
            "metadata": dict(self.metadata),
        }


# ── Transitions & Evolution Events ───────────────────────────────────────────

class IntentStateTransition(BaseModel):
    """
    Explicit transition record from one lifecycle state to another.
    """
    model_config = ConfigDict(frozen=True)

    transition_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    from_state: IntentLifecycleState
    to_state: IntentLifecycleState
    transition_reason: str = ""
    transitioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_event_type: Optional[IntentEvolutionEventType] = None
    confidence_delta: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": str(self.transition_id),
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "transition_reason": self.transition_reason,
            "transitioned_at": self.transitioned_at.isoformat(),
            "trigger_event_type": self.trigger_event_type.value if self.trigger_event_type else None,
            "confidence_delta": self.confidence_delta,
            "metadata": dict(self.metadata),
        }


class IntentEvolutionEvent(BaseModel):
    """
    Immutable evolution event. The definitive historical source of truth.
    """
    model_config = ConfigDict(frozen=True)

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    intent_id: uuid.UUID
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    event_type: IntentEvolutionEventType
    previous_state: Optional[IntentLifecycleState] = None
    current_state: IntentLifecycleState
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supporting_evidence: List[str] = Field(default_factory=list)
    source_conversations: List[str] = Field(default_factory=list)
    provenance: EvolutionProvenance = Field(default_factory=EvolutionProvenance)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "intent_id": str(self.intent_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "event_type": self.event_type.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "current_state": self.current_state.value,
            "occurred_at": self.occurred_at.isoformat(),
            "supporting_evidence": list(self.supporting_evidence),
            "source_conversations": list(self.source_conversations),
            "provenance": self.provenance.to_dict(),
            "metadata": dict(self.metadata),
        }


class IntentEvolutionEventStream(BaseModel):
    """
    Append-only stream of evolution events for an entity.
    Future projections (Customer Journey, Executive Dashboard, Analytics) rebuild from this stream.
    """
    model_config = ConfigDict(frozen=True)

    stream_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str = ""
    workspace_id: Optional[uuid.UUID] = None
    events: List[IntentEvolutionEvent] = Field(default_factory=list)
    version: int = 1
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def append(self, event: IntentEvolutionEvent) -> IntentEvolutionEventStream:
        """Return a new immutable stream instance with the event appended."""
        new_events = list(self.events) + [event]
        return IntentEvolutionEventStream(
            stream_id=self.stream_id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            workspace_id=self.workspace_id,
            events=new_events,
            version=self.version + 1,
            updated_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_id": str(self.stream_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "events": [e.to_dict() for e in self.events],
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
        }


# ── Timelines & History Aggregates ───────────────────────────────────────────

class IntentTimeline(BaseModel):
    """
    Chronological projection of an intent's trajectory over time.
    """
    model_config = ConfigDict(frozen=True)

    timeline_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    intent_id: uuid.UUID
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str
    intent_name: str
    taxonomy_path: str
    first_detected_at: datetime
    last_observed_at: datetime
    observation_frequency: int = 1
    velocity: IntentVelocity = IntentVelocity.UNKNOWN
    source_conversations: List[str] = Field(default_factory=list)
    state_transitions: List[IntentStateTransition] = Field(default_factory=list)
    classification_history: List[Dict[str, Any]] = Field(default_factory=list)
    relationship_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_lifecycle_state: IntentLifecycleState = IntentLifecycleState.NEW
    current_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": str(self.timeline_id),
            "intent_id": str(self.intent_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "intent_name": self.intent_name,
            "taxonomy_path": self.taxonomy_path,
            "first_detected_at": self.first_detected_at.isoformat(),
            "last_observed_at": self.last_observed_at.isoformat(),
            "observation_frequency": self.observation_frequency,
            "velocity": self.velocity.value,
            "source_conversations": list(self.source_conversations),
            "state_transitions": [t.to_dict() for t in self.state_transitions],
            "classification_history": [dict(c) for c in self.classification_history],
            "relationship_history": [dict(r) for r in self.relationship_history],
            "current_lifecycle_state": self.current_lifecycle_state.value,
            "current_confidence": self.current_confidence,
            "metadata": dict(self.metadata),
        }


class IntentHistory(BaseModel):
    """
    Cumulative multi-conversation history for a distinct intent.
    """
    model_config = ConfigDict(frozen=True)

    history_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    intent_id: uuid.UUID
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    canonical_intent_name: str
    current_state: IntentLifecycleState
    timeline: IntentTimeline
    snapshots: List[IntentStateSnapshot] = Field(default_factory=list)
    events: List[IntentEvolutionEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history_id": str(self.history_id),
            "intent_id": str(self.intent_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "canonical_intent_name": self.canonical_intent_name,
            "current_state": self.current_state.value,
            "timeline": self.timeline.to_dict(),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "events": [e.to_dict() for e in self.events],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ── Telemetry, Diagnostics & Aggregate Root ─────────────────────────────────

class EvolutionMetadata(BaseModel):
    """Aggregate statistics and distribution metrics for intent evolution."""
    model_config = ConfigDict(frozen=True)

    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str = ""
    workspace_id: Optional[uuid.UUID] = None
    total_active_intents: int = 0
    total_persisting_intents: int = 0
    total_strengthening_intents: int = 0
    total_weakening_intents: int = 0
    total_resolved_intents: int = 0
    total_closed_intents: int = 0
    total_events_generated: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "total_active_intents": self.total_active_intents,
            "total_persisting_intents": self.total_persisting_intents,
            "total_strengthening_intents": self.total_strengthening_intents,
            "total_weakening_intents": self.total_weakening_intents,
            "total_resolved_intents": self.total_resolved_intents,
            "total_closed_intents": self.total_closed_intents,
            "total_events_generated": self.total_events_generated,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class EvolutionDiagnostics(BaseModel):
    """Performance metrics and invariant validation reports."""
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float = 0.0
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    stages_executed: List[str] = Field(default_factory=list)
    snapshots_compared: int = 0
    strategies_evaluated: int = 0
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_execution_time_ms": self.pipeline_execution_time_ms,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "stages_executed": list(self.stages_executed),
            "snapshots_compared": self.snapshots_compared,
            "strategies_evaluated": self.strategies_evaluated,
            "is_valid": self.is_valid,
            "validation_errors": list(self.validation_errors),
            "warnings": list(self.warnings),
        }


class IntentEvolutionResult(BaseModel):
    """
    Immutable aggregate root emitted by the Intent Evolution Engine.
    Official temporal intelligence artifact.
    """
    model_config = ConfigDict(frozen=True)

    evolution_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_type: EntityType = EntityType.CUSTOMER
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    current_conversation_id: str
    intent_histories: List[IntentHistory] = Field(default_factory=list)
    timelines: List[IntentTimeline] = Field(default_factory=list)
    event_stream: IntentEvolutionEventStream = Field(default_factory=IntentEvolutionEventStream)
    metadata: EvolutionMetadata = Field(default_factory=EvolutionMetadata)
    diagnostics: EvolutionDiagnostics = Field(default_factory=EvolutionDiagnostics)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def customer_id(self) -> Optional[str]:
        """Convenience property for customer-centric workflows."""
        return self.entity_id if self.entity_type == EntityType.CUSTOMER else None

    def get_history_by_intent(self, intent_id: uuid.UUID) -> Optional[IntentHistory]:
        for h in self.intent_histories:
            if h.intent_id == intent_id:
                return h
        return None

    def get_timeline_by_intent(self, intent_id: uuid.UUID) -> Optional[IntentTimeline]:
        for t in self.timelines:
            if t.intent_id == intent_id:
                return t
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evolution_id": str(self.evolution_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "current_conversation_id": self.current_conversation_id,
            "intent_histories": [h.to_dict() for h in self.intent_histories],
            "timelines": [t.to_dict() for t in self.timelines],
            "event_stream": self.event_stream.to_dict(),
            "metadata": self.metadata.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }
