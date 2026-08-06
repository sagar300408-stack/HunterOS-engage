"""
HunterOS Engage — Conversation Analysis Pydantic Schemas (Phase 2.2.1)

Pydantic v2 DTOs for client requests and structured query responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.conversations.analysis.models import (
    FactCategory,
    MessageDirection,
    SegmentType,
    SummaryType,
)


# ── Request DTOs ──────────────────────────────────────────────────────────────

class MessageInputDTO(BaseModel):
    """Input payload for an individual conversation message."""
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    sender: str = "customer"
    content: str
    timestamp: Optional[datetime] = None
    direction: Optional[str] = None
    channel: str = "whatsapp"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeConversationRequest(BaseModel):
    """Request to initiate conversation analysis."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    messages: List[MessageInputDTO] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── Response DTOs ─────────────────────────────────────────────────────────────

class SourceMessageRefDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    timestamp: Optional[datetime] = None
    text_snippet: Optional[str] = None


class ArtifactProvenanceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_id: uuid.UUID
    pipeline_stage: str
    generated_at: datetime
    generator_version: str
    confidence: float
    source_messages: List[SourceMessageRefDTO] = Field(default_factory=list)
    extraction_method: str


class CanonicalValueDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_value: Any
    normalized_value: Any
    data_type: str
    unit: Optional[str] = None
    formatted: Optional[str] = None


class ExtractedFactDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fact_id: uuid.UUID
    category: FactCategory
    key: str
    raw_value: Any
    canonical_value: CanonicalValueDTO
    provenance: ArtifactProvenanceDTO
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSegmentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: uuid.UUID
    segment_type: SegmentType
    custom_label: Optional[str] = None
    start_message_id: str
    end_message_id: str
    message_count: int
    summary_snippet: Optional[str] = None
    provenance: ArtifactProvenanceDTO


class TopicDistributionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_name: str
    taxonomy_path: str
    category: str
    frequency: int
    weight: float
    provenance: ArtifactProvenanceDTO
    first_mentioned_at: Optional[datetime] = None
    last_mentioned_at: Optional[datetime] = None


class TopicTimelineItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_name: str
    taxonomy_path: str
    message_id: str
    timestamp: datetime
    position_fraction: float


class TopicAnalysisDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    primary_topic: str
    primary_taxonomy_path: str
    secondary_topics: List[str] = Field(default_factory=list)
    distribution: List[TopicDistributionDTO] = Field(default_factory=list)
    timeline: List[TopicTimelineItemDTO] = Field(default_factory=list)
    provenance: ArtifactProvenanceDTO


class ConversationSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary_id: uuid.UUID
    summary_type: SummaryType
    template_name: str
    content: str
    key_points: List[str] = Field(default_factory=list)
    provenance: ArtifactProvenanceDTO
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationMetadataDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    duration_seconds: float
    message_count: int
    incoming_count: int
    outgoing_count: int
    participants: List[str] = Field(default_factory=list)
    communication_channels: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    message_types: List[str] = Field(default_factory=list)
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None


class AnalysisDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    stages_executed: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool


class ConversationAnalysisResponse(BaseModel):
    """Unified response aggregate for conversation analysis."""
    model_config = ConfigDict(from_attributes=True)

    analysis_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    analyzed_at: datetime
    schema_version: str

    metadata: ConversationMetadataDTO
    segments: List[ConversationSegmentDTO] = Field(default_factory=list)
    topics: TopicAnalysisDTO
    facts: List[ExtractedFactDTO] = Field(default_factory=list)
    summaries: Dict[str, ConversationSummaryDTO] = Field(default_factory=dict)
    custom_artifacts: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: AnalysisDiagnosticsDTO
