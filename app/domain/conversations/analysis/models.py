"""
HunterOS Engage — Conversation Analysis Domain Models (Phase 2.2.1)

Defines immutable domain models, enums, value objects, provenance structures,
and aggregate roots for deterministic conversation analysis.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class SegmentType(str, enum.Enum):
    """Conversational stage/phase types."""
    GREETING = "GREETING"
    DISCOVERY = "DISCOVERY"
    DISCUSSION = "DISCUSSION"
    NEGOTIATION = "NEGOTIATION"
    CLOSING = "CLOSING"
    FOLLOW_UP = "FOLLOW_UP"
    CUSTOM = "CUSTOM"


class FactCategory(str, enum.Enum):
    """Classification of extracted key facts."""
    CUSTOMER_INFO = "CUSTOMER_INFO"
    COMPANY_INFO = "COMPANY_INFO"
    PRODUCT_REFERENCE = "PRODUCT_REFERENCE"
    PROPERTY_REFERENCE = "PROPERTY_REFERENCE"
    BUDGET_REFERENCE = "BUDGET_REFERENCE"
    DATE_REFERENCE = "DATE_REFERENCE"
    LOCATION_REFERENCE = "LOCATION_REFERENCE"
    CONTACT_INFO = "CONTACT_INFO"
    DOCUMENT_MENTIONED = "DOCUMENT_MENTIONED"
    CUSTOM = "CUSTOM"


class SummaryType(str, enum.Enum):
    """Target perspective of conversation summaries."""
    EXECUTIVE = "EXECUTIVE"
    CUSTOMER = "CUSTOMER"
    INTERNAL = "INTERNAL"
    TECHNICAL = "TECHNICAL"
    CUSTOM = "CUSTOM"


class ExtractionMethod(str, enum.Enum):
    """Deterministic extraction mechanism."""
    RULE_BASED = "RULE_BASED"
    PATTERN_MATCHER = "PATTERN_MATCHER"
    HEURISTIC = "HEURISTIC"
    COMPUTATIONAL = "COMPUTATIONAL"
    TEMPLATE = "TEMPLATE"
    REGISTRY = "REGISTRY"


class MessageDirection(str, enum.Enum):
    """Direction of normalized message."""
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    SYSTEM = "SYSTEM"


class PipelineState(str, enum.Enum):
    """Lifecycle state of conversation analysis pipeline execution."""
    INITIALIZED = "INITIALIZED"
    LOADING = "LOADING"
    NORMALIZING = "NORMALIZING"
    SEGMENTING = "SEGMENTING"
    DETECTING_TOPICS = "DETECTING_TOPICS"
    EXTRACTING_FACTS = "EXTRACTING_FACTS"
    NORMALIZING_FACTS = "NORMALIZING_FACTS"
    SUMMARIZING = "SUMMARIZING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── Value Objects & Provenance ────────────────────────────────────────────────

class SourceMessageRef(BaseModel):
    """Direct pointer to source message supporting lineage and auditability."""
    model_config = ConfigDict(frozen=True)

    message_id: str
    timestamp: Optional[datetime] = None
    text_snippet: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ArtifactProvenance(BaseModel):
    """Detailed origin, generator metadata, and confidence tracking for every artifact."""
    model_config = ConfigDict(frozen=True)

    artifact_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    pipeline_stage: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generator_version: str = "1.0.0"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_messages: List[SourceMessageRef] = Field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.RULE_BASED


class CanonicalValue(BaseModel):
    """Standardized representation of an extracted fact value."""
    model_config = ConfigDict(frozen=True)

    raw_value: Any
    normalized_value: Any
    data_type: str  # e.g., 'currency', 'number', 'date', 'phone', 'email', 'string'
    unit: Optional[str] = None  # e.g., 'INR', 'USD', 'sqft', 'ISO8601'
    formatted: Optional[str] = None


class NormalizedMessage(BaseModel):
    """Normalized message representation stripped of transport noise."""
    model_config = ConfigDict(frozen=True)

    id: str
    conversation_id: Optional[str] = None
    direction: MessageDirection
    sender: str
    content: str
    cleaned_content: str
    timestamp: datetime
    channel: str = "whatsapp"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── Domain Entities ───────────────────────────────────────────────────────────

class ConversationSegment(BaseModel):
    """Identified distinct conversational stage."""
    model_config = ConfigDict(frozen=True)

    segment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    segment_type: SegmentType
    custom_label: Optional[str] = None
    start_message_id: str
    end_message_id: str
    message_count: int
    summary_snippet: Optional[str] = None
    provenance: ArtifactProvenance


class TopicDistribution(BaseModel):
    """Frequency and weight metric for a single detected topic."""
    model_config = ConfigDict(frozen=True)

    topic_name: str
    taxonomy_path: str
    category: str
    frequency: int
    weight: float
    provenance: ArtifactProvenance
    first_mentioned_at: Optional[datetime] = None
    last_mentioned_at: Optional[datetime] = None


class TopicTimelineItem(BaseModel):
    """Chronological occurrence point of a topic within conversation."""
    model_config = ConfigDict(frozen=True)

    topic_name: str
    taxonomy_path: str
    message_id: str
    timestamp: datetime
    position_fraction: float  # 0.0 to 1.0


class TopicAnalysis(BaseModel):
    """Comprehensive topic analysis aggregate."""
    model_config = ConfigDict(frozen=True)

    primary_topic: str
    primary_taxonomy_path: str
    secondary_topics: List[str] = Field(default_factory=list)
    distribution: List[TopicDistribution] = Field(default_factory=list)
    timeline: List[TopicTimelineItem] = Field(default_factory=list)
    provenance: ArtifactProvenance


class ExtractedFact(BaseModel):
    """Discrete key business fact extracted with canonical value and provenance."""
    model_config = ConfigDict(frozen=True)

    fact_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category: FactCategory
    key: str
    raw_value: Any
    canonical_value: CanonicalValue
    provenance: ArtifactProvenance
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    """Structured multi-perspective summary of the conversation."""
    model_config = ConfigDict(frozen=True)

    summary_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    summary_type: SummaryType
    template_name: str
    content: str
    key_points: List[str] = Field(default_factory=list)
    provenance: ArtifactProvenance
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationMetadata(BaseModel):
    """Descriptive structural metadata of a conversation."""
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    duration_seconds: float = 0.0
    message_count: int = 0
    incoming_count: int = 0
    outgoing_count: int = 0
    participants: List[str] = Field(default_factory=list)
    communication_channels: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    message_types: List[str] = Field(default_factory=list)
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None


class AnalysisDiagnostics(BaseModel):
    """Telemetry, execution timing, and diagnostic reports."""
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float = 0.0
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    stages_executed: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


# ── Aggregate Root ────────────────────────────────────────────────────────────

class ConversationAnalysisResult(BaseModel):
    """
    Immutable aggregate root containing the complete structured analysis
    of a conversation. This is the official artifact emitted by Conversation Analysis.
    """
    model_config = ConfigDict(frozen=True)

    analysis_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    metadata: ConversationMetadata
    segments: List[ConversationSegment] = Field(default_factory=list)
    topics: TopicAnalysis
    facts: List[ExtractedFact] = Field(default_factory=list)
    summaries: Dict[str, ConversationSummary] = Field(default_factory=dict)
    custom_artifacts: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: AnalysisDiagnostics
