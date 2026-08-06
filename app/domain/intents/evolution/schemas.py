"""
HunterOS Engage V1 - Intent Evolution API Schemas (Pydantic V2)
Request/Response contracts for Intent History & Evolution REST endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEventType,
    IntentLifecycleState,
    IntentVelocity,
)


class EvolveIntentsRequest(BaseModel):
    """Request payload to compute evolution across historical and current intents."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: str = Field(..., description="Current active conversation ID")
    entity_id: str = Field(..., description="Unique entity identifier (e.g. customer_id, deal_id)")
    entity_type: EntityType = Field(default=EntityType.CUSTOMER, description="Entity type")
    workspace_id: Optional[uuid.UUID] = Field(default=None, description="Tenant workspace ID")
    conversation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Conversation metadata")


class IntentStateTransitionDTO(BaseModel):
    """DTO representing a single lifecycle state transition."""
    model_config = ConfigDict(from_attributes=True)

    transition_id: uuid.UUID
    from_state: IntentLifecycleState
    to_state: IntentLifecycleState
    transition_reason: str
    transitioned_at: datetime
    trigger_event_type: Optional[IntentEvolutionEventType] = None
    confidence_delta: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentEvolutionEventDTO(BaseModel):
    """DTO representing an evolution audit event."""
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    intent_id: uuid.UUID
    entity_type: EntityType
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    event_type: IntentEvolutionEventType
    previous_state: Optional[IntentLifecycleState] = None
    current_state: IntentLifecycleState
    occurred_at: datetime
    supporting_evidence: List[str] = Field(default_factory=list)
    source_conversations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentTimelineDTO(BaseModel):
    """DTO for projected intent timeline."""
    model_config = ConfigDict(from_attributes=True)

    timeline_id: uuid.UUID
    intent_id: uuid.UUID
    entity_type: EntityType
    entity_id: str
    intent_name: str
    taxonomy_path: str
    first_detected_at: datetime
    last_observed_at: datetime
    observation_frequency: int
    velocity: IntentVelocity
    source_conversations: List[str]
    state_transitions: List[IntentStateTransitionDTO]
    current_lifecycle_state: IntentLifecycleState
    current_confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentStateSnapshotDTO(BaseModel):
    """DTO for a historical point-in-time intent state snapshot."""
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: uuid.UUID
    intent_id: uuid.UUID
    entity_type: EntityType
    entity_id: str
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    intent_type: str
    category: str
    taxonomy_path: str
    confidence: float
    observed_at: datetime
    evidence_message_ids: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentHistoryDTO(BaseModel):
    """DTO for cumulative intent history."""
    model_config = ConfigDict(from_attributes=True)

    history_id: uuid.UUID
    intent_id: uuid.UUID
    entity_type: EntityType
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    canonical_intent_name: str
    current_state: IntentLifecycleState
    timeline: IntentTimelineDTO
    snapshots: List[IntentStateSnapshotDTO]
    events: List[IntentEvolutionEventDTO]
    created_at: datetime
    updated_at: datetime


class EvolutionMetadataDTO(BaseModel):
    """DTO for aggregate evolution metadata."""
    model_config = ConfigDict(from_attributes=True)

    entity_type: EntityType
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    total_active_intents: int
    total_persisting_intents: int
    total_strengthening_intents: int
    total_weakening_intents: int
    total_resolved_intents: int
    total_closed_intents: int
    total_events_generated: int
    evaluated_at: datetime


class EvolutionDiagnosticsDTO(BaseModel):
    """DTO for pipeline execution diagnostics."""
    model_config = ConfigDict(from_attributes=True)

    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float]
    stages_executed: List[str]
    snapshots_compared: int
    strategies_evaluated: int
    is_valid: bool
    validation_errors: List[str]
    warnings: List[str]


class IntentEvolutionResultDTO(BaseModel):
    """Top-level DTO for intent evolution results."""
    model_config = ConfigDict(from_attributes=True)

    evolution_id: uuid.UUID
    entity_type: EntityType
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    current_conversation_id: str
    intent_histories: List[IntentHistoryDTO]
    timelines: List[IntentTimelineDTO]
    metadata: EvolutionMetadataDTO
    diagnostics: EvolutionDiagnosticsDTO
    generated_at: datetime


class IntentEvolutionAnalyticsDTO(BaseModel):
    """Descriptive query analytics DTO."""
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    entity_type: EntityType
    workspace_id: Optional[uuid.UUID] = None
    total_evolutions: int
    evolution_frequency: float
    state_distribution: Dict[str, int]
    transition_distribution: Dict[str, int]
    merge_count: int
    split_count: int
    lifecycle_duration_days: float
    average_velocity: str
    generated_at: datetime
