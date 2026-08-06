"""
HunterOS Engage V1 - Conversation Timeline Domain Models
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic, immutable business timeline domain entities, event streams, milestones,
important moments, and provenance tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TimelineScopeType(str, Enum):
    CONVERSATION = "CONVERSATION"
    CUSTOMER = "CUSTOMER"
    WORKSPACE = "WORKSPACE"


class TimelineEventType(str, Enum):
    CONVERSATION_STARTED = "CONVERSATION_STARTED"
    CUSTOMER_INTRODUCED = "CUSTOMER_INTRODUCED"
    REQUIREMENT_IDENTIFIED = "REQUIREMENT_IDENTIFIED"
    QUESTION_ASKED = "QUESTION_ASKED"
    INFORMATION_SHARED = "INFORMATION_SHARED"
    BUDGET_MENTIONED = "BUDGET_MENTIONED"
    DATE_MENTIONED = "DATE_MENTIONED"
    DOCUMENT_SHARED = "DOCUMENT_SHARED"
    MEETING_SCHEDULED = "MEETING_SCHEDULED"
    MEETING_COMPLETED = "MEETING_COMPLETED"
    OBJECTION_RAISED = "OBJECTION_RAISED"
    AGREEMENT_REACHED = "AGREEMENT_REACHED"
    FOLLOW_UP_REQUESTED = "FOLLOW_UP_REQUESTED"
    CONVERSATION_CLOSED = "CONVERSATION_CLOSED"
    CUSTOM_EVENT = "CUSTOM_EVENT"


class TimelineEventCategory(str, Enum):
    COMMUNICATION = "COMMUNICATION"
    REQUIREMENT = "REQUIREMENT"
    FINANCIAL = "FINANCIAL"
    SCHEDULING = "SCHEDULING"
    COMMITMENT = "COMMITMENT"
    OBJECTION = "OBJECTION"
    DOCUMENT = "DOCUMENT"
    LIFECYCLE = "LIFECYCLE"
    CUSTOM = "CUSTOM"


class MilestoneType(str, Enum):
    INITIAL_ENGAGEMENT = "INITIAL_ENGAGEMENT"
    NEEDS_ALIGNED = "NEEDS_ALIGNED"
    BUDGET_ESTABLISHED = "BUDGET_ESTABLISHED"
    COMMERCIAL_TERMS_DISCUSSED = "COMMERCIAL_TERMS_DISCUSSED"
    APPOINTMENT_COMMITTED = "APPOINTMENT_COMMITTED"
    COMMITMENT_FINALIZED = "COMMITMENT_FINALIZED"
    SESSION_CONCLUDED = "SESSION_CONCLUDED"
    CUSTOM_MILESTONE = "CUSTOM_MILESTONE"


class ImportantMomentType(str, Enum):
    FIRST_REQUIREMENT = "FIRST_REQUIREMENT"
    BUDGET_DISCUSSION = "BUDGET_DISCUSSION"
    FIRST_COMMITMENT = "FIRST_COMMITMENT"
    FIRST_OBJECTION = "FIRST_OBJECTION"
    DOCUMENT_EXCHANGE = "DOCUMENT_EXCHANGE"
    MEETING_CONFIRMATION = "MEETING_CONFIRMATION"
    CUSTOMER_DECISION_STATEMENT = "CUSTOMER_DECISION_STATEMENT"
    CUSTOM_IMPORTANT_MOMENT = "CUSTOM_IMPORTANT_MOMENT"


class TimelineViewType(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    DETAILED = "DETAILED"
    COMPACT = "COMPACT"
    AUDIT = "AUDIT"


class TimelineViewFormat(str, Enum):
    CHRONOLOGICAL_EVENTS = "CHRONOLOGICAL_EVENTS"
    MILESTONES_ONLY = "MILESTONES_ONLY"
    IMPORTANT_MOMENTS = "IMPORTANT_MOMENTS"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    PARTICIPANT_TIMELINE = "PARTICIPANT_TIMELINE"
    CUSTOM_VIEW = "CUSTOM_VIEW"


class TimelinePipelineState(str, Enum):
    INITIALIZING = "INITIALIZING"
    LOADING = "LOADING"
    EXTRACTING_EVENTS = "EXTRACTING_EVENTS"
    NORMALIZING = "NORMALIZING"
    ORDERING = "ORDERING"
    DETECTING_MILESTONES = "DETECTING_MILESTONES"
    DETECTING_MOMENTS = "DETECTING_MOMENTS"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class TimelineProvenance:
    """Full hierarchical lineage and traceability for a timeline event."""
    analysis_id: uuid.UUID
    fact_id: Optional[uuid.UUID] = None
    segment_id: Optional[uuid.UUID] = None
    source_message_ids: List[str] = field(default_factory=list)
    pipeline_stage: str = "EXTRACT_EVENTS"
    generator_version: str = "2.2.2"
    confidence: float = 1.0
    extraction_method: str = "DETERMINISTIC_EXTRACTION"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": str(self.analysis_id),
            "fact_id": str(self.fact_id) if self.fact_id else None,
            "segment_id": str(self.segment_id) if self.segment_id else None,
            "source_message_ids": list(self.source_message_ids),
            "pipeline_stage": self.pipeline_stage,
            "generator_version": self.generator_version,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineProvenance:
        return cls(
            analysis_id=uuid.UUID(str(data["analysis_id"])),
            fact_id=uuid.UUID(str(data["fact_id"])) if data.get("fact_id") else None,
            segment_id=uuid.UUID(str(data["segment_id"])) if data.get("segment_id") else None,
            source_message_ids=list(data.get("source_message_ids", [])),
            pipeline_stage=data.get("pipeline_stage", "EXTRACT_EVENTS"),
            generator_version=data.get("generator_version", "2.2.2"),
            confidence=float(data.get("confidence", 1.0)),
            extraction_method=data.get("extraction_method", "DETERMINISTIC_EXTRACTION"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class TimelineEvent:
    """Immutable single atomic chronological event in a conversation."""
    event_id: uuid.UUID
    conversation_id: Optional[str]
    workspace_id: Optional[uuid.UUID]
    event_type: TimelineEventType
    category: TimelineEventCategory
    title: str
    description: str
    occurred_at: datetime
    sequence_index: int = 0
    time_offset_seconds: float = 0.0
    provenance: Optional[TimelineProvenance] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "event_type": self.event_type.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "occurred_at": self.occurred_at.isoformat(),
            "sequence_index": self.sequence_index,
            "time_offset_seconds": self.time_offset_seconds,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineEvent:
        occurred_raw = data["occurred_at"]
        occurred_dt = datetime.fromisoformat(occurred_raw) if isinstance(occurred_raw, str) else occurred_raw
        if occurred_dt.tzinfo is None:
            occurred_dt = occurred_dt.replace(tzinfo=timezone.utc)

        created_raw = data.get("created_at")
        if created_raw:
            created_dt = datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
        else:
            created_dt = datetime.now(timezone.utc)

        return cls(
            event_id=uuid.UUID(str(data["event_id"])),
            conversation_id=data.get("conversation_id"),
            workspace_id=uuid.UUID(str(data["workspace_id"])) if data.get("workspace_id") else None,
            event_type=TimelineEventType(data["event_type"]),
            category=TimelineEventCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            occurred_at=occurred_dt,
            sequence_index=int(data.get("sequence_index", 0)),
            time_offset_seconds=float(data.get("time_offset_seconds", 0.0)),
            provenance=TimelineProvenance.from_dict(data["provenance"]) if data.get("provenance") else None,
            confidence=float(data.get("confidence", 1.0)),
            metadata=dict(data.get("metadata", {})),
            created_at=created_dt,
        )


@dataclass(frozen=True)
class TimelineMilestone:
    """Significant business milestone detected across a collection of events."""
    milestone_id: uuid.UUID
    milestone_type: MilestoneType
    title: str
    description: str
    timestamp: datetime
    source_event_ids: List[uuid.UUID] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": str(self.milestone_id),
            "milestone_type": self.milestone_type.value,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "source_event_ids": [str(eid) for eid in self.source_event_ids],
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineMilestone:
        ts_raw = data["timestamp"]
        ts_dt = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        return cls(
            milestone_id=uuid.UUID(str(data["milestone_id"])),
            milestone_type=MilestoneType(data["milestone_type"]),
            title=data["title"],
            description=data["description"],
            timestamp=ts_dt,
            source_event_ids=[uuid.UUID(str(eid)) for eid in data.get("source_event_ids", [])],
            confidence=float(data.get("confidence", 1.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ImportantMoment:
    """High-value decisive conversational moment."""
    moment_id: uuid.UUID
    moment_type: ImportantMomentType
    title: str
    significance: str
    timestamp: datetime
    source_event_id: Optional[uuid.UUID] = None
    source_message_id: Optional[str] = None
    snippet: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moment_id": str(self.moment_id),
            "moment_type": self.moment_type.value,
            "title": self.title,
            "significance": self.significance,
            "timestamp": self.timestamp.isoformat(),
            "source_event_id": str(self.source_event_id) if self.source_event_id else None,
            "source_message_id": self.source_message_id,
            "snippet": self.snippet,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImportantMoment:
        ts_raw = data["timestamp"]
        ts_dt = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        return cls(
            moment_id=uuid.UUID(str(data["moment_id"])),
            moment_type=ImportantMomentType(data["moment_type"]),
            title=data["title"],
            significance=data["significance"],
            timestamp=ts_dt,
            source_event_id=uuid.UUID(str(data["source_event_id"])) if data.get("source_event_id") else None,
            source_message_id=data.get("source_message_id"),
            snippet=data.get("snippet", ""),
            confidence=float(data.get("confidence", 1.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ConversationEventStream:
    """Immutable sequence of chronological events forming the audit stream."""
    stream_id: uuid.UUID
    conversation_id: Optional[str]
    workspace_id: Optional[uuid.UUID]
    customer_id: Optional[str]
    events: List[TimelineEvent] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_events(self) -> int:
        return len(self.events)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_id": str(self.stream_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "events": [e.to_dict() for e in self.events],
            "total_events": self.total_events,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationEventStream:
        start_raw = data.get("start_time")
        end_raw = data.get("end_time")
        created_raw = data.get("created_at")

        start_dt = datetime.fromisoformat(start_raw) if isinstance(start_raw, str) else start_raw
        if start_dt and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(end_raw) if isinstance(end_raw, str) else end_raw
        if end_dt and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        created_dt = datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
        if created_dt and created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        elif not created_dt:
            created_dt = datetime.now(timezone.utc)

        return cls(
            stream_id=uuid.UUID(str(data["stream_id"])),
            conversation_id=data.get("conversation_id"),
            workspace_id=uuid.UUID(str(data["workspace_id"])) if data.get("workspace_id") else None,
            customer_id=data.get("customer_id"),
            events=[TimelineEvent.from_dict(e) for e in data.get("events", [])],
            start_time=start_dt,
            end_time=end_dt,
            created_at=created_dt,
        )


@dataclass(frozen=True)
class TimelineMetadata:
    """Descriptive metadata and category statistics for the timeline projection."""
    timeline_id: uuid.UUID
    conversation_id: Optional[str]
    workspace_id: Optional[uuid.UUID]
    customer_id: Optional[str]
    scope_type: TimelineScopeType
    total_events: int
    total_milestones: int
    total_moments: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: float
    event_category_distribution: Dict[str, int]
    timeline_version: int = 1
    schema_version: str = "1.0.0"
    generator_version: str = "2.2.2"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": str(self.timeline_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "scope_type": self.scope_type.value,
            "total_events": self.total_events,
            "total_milestones": self.total_milestones,
            "total_moments": self.total_moments,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "event_category_distribution": dict(self.event_category_distribution),
            "timeline_version": self.timeline_version,
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineMetadata:
        start_raw = data.get("start_time")
        end_raw = data.get("end_time")
        gen_raw = data.get("generated_at")

        start_dt = datetime.fromisoformat(start_raw) if isinstance(start_raw, str) else start_raw
        if start_dt and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(end_raw) if isinstance(end_raw, str) else end_raw
        if end_dt and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        gen_dt = datetime.fromisoformat(gen_raw) if isinstance(gen_raw, str) else gen_raw
        if gen_dt and gen_dt.tzinfo is None:
            gen_dt = gen_dt.replace(tzinfo=timezone.utc)
        elif not gen_dt:
            gen_dt = datetime.now(timezone.utc)

        return cls(
            timeline_id=uuid.UUID(str(data["timeline_id"])),
            conversation_id=data.get("conversation_id"),
            workspace_id=uuid.UUID(str(data["workspace_id"])) if data.get("workspace_id") else None,
            customer_id=data.get("customer_id"),
            scope_type=TimelineScopeType(data.get("scope_type", TimelineScopeType.CONVERSATION.value)),
            total_events=int(data.get("total_events", 0)),
            total_milestones=int(data.get("total_milestones", 0)),
            total_moments=int(data.get("total_moments", 0)),
            start_time=start_dt,
            end_time=end_dt,
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            event_category_distribution=dict(data.get("event_category_distribution", {})),
            timeline_version=int(data.get("timeline_version", 1)),
            schema_version=data.get("schema_version", "1.0.0"),
            generator_version=data.get("generator_version", "2.2.2"),
            generated_at=gen_dt,
        )


@dataclass(frozen=True)
class TimelineDiagnostics:
    """Operational timing metrics and validation results for pipeline execution."""
    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    stages_executed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_execution_time_ms": self.pipeline_execution_time_ms,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "stages_executed": list(self.stages_executed),
            "warnings": list(self.warnings),
            "validation_errors": list(self.validation_errors),
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineDiagnostics:
        return cls(
            pipeline_execution_time_ms=float(data.get("pipeline_execution_time_ms", 0.0)),
            stage_timings_ms=dict(data.get("stage_timings_ms", {})),
            stages_executed=list(data.get("stages_executed", [])),
            warnings=list(data.get("warnings", [])),
            validation_errors=list(data.get("validation_errors", [])),
            is_valid=bool(data.get("is_valid", True)),
        )


@dataclass(frozen=True)
class ConversationTimeline:
    """Immutable aggregate root projection representing the synthesized timeline."""
    timeline_id: uuid.UUID
    conversation_id: Optional[str]
    workspace_id: Optional[uuid.UUID]
    customer_id: Optional[str]
    scope_type: TimelineScopeType
    metadata: TimelineMetadata
    event_stream: ConversationEventStream
    milestones: List[TimelineMilestone] = field(default_factory=list)
    important_moments: List[ImportantMoment] = field(default_factory=list)
    diagnostics: Optional[TimelineDiagnostics] = None
    timeline_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def events(self) -> List[TimelineEvent]:
        return self.event_stream.events

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": str(self.timeline_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "scope_type": self.scope_type.value,
            "metadata": self.metadata.to_dict(),
            "event_stream": self.event_stream.to_dict(),
            "milestones": [m.to_dict() for m in self.milestones],
            "important_moments": [m.to_dict() for m in self.important_moments],
            "diagnostics": self.diagnostics.to_dict() if self.diagnostics else None,
            "timeline_version": self.timeline_version,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationTimeline:
        created_raw = data.get("created_at")
        created_dt = datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
        if created_dt and created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        elif not created_dt:
            created_dt = datetime.now(timezone.utc)

        return cls(
            timeline_id=uuid.UUID(str(data["timeline_id"])),
            conversation_id=data.get("conversation_id"),
            workspace_id=uuid.UUID(str(data["workspace_id"])) if data.get("workspace_id") else None,
            customer_id=data.get("customer_id"),
            scope_type=TimelineScopeType(data.get("scope_type", TimelineScopeType.CONVERSATION.value)),
            metadata=TimelineMetadata.from_dict(data["metadata"]),
            event_stream=ConversationEventStream.from_dict(data["event_stream"]),
            milestones=[TimelineMilestone.from_dict(m) for m in data.get("milestones", [])],
            important_moments=[ImportantMoment.from_dict(m) for m in data.get("important_moments", [])],
            diagnostics=TimelineDiagnostics.from_dict(data["diagnostics"]) if data.get("diagnostics") else None,
            timeline_version=int(data.get("timeline_version", 1)),
            created_at=created_dt,
        )
