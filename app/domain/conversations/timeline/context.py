"""
HunterOS Engage V1 - Conversation Timeline Execution Context
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Shared state container and lifecycle state machine for the timeline construction pipeline.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ExtractedFact,
    TopicAnalysis,
)
from app.domain.conversations.timeline.models import (
    ConversationEventStream,
    ConversationTimeline,
    ImportantMoment,
    TimelineDiagnostics,
    TimelineEvent,
    TimelineMetadata,
    TimelineMilestone,
    TimelinePipelineState,
    TimelineScopeType,
)


@dataclass
class ConversationTimelineContext:
    """Execution context passed across all timeline construction pipeline stages."""
    analysis_result: Optional[ConversationAnalysisResult] = None
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    scope_type: TimelineScopeType = TimelineScopeType.CONVERSATION

    # Event accumulators
    raw_events: List[TimelineEvent] = field(default_factory=list)
    normalized_events: List[TimelineEvent] = field(default_factory=list)

    # Synthesized projections
    milestones: List[TimelineMilestone] = field(default_factory=list)
    important_moments: List[ImportantMoment] = field(default_factory=list)

    # Final outputs
    event_stream: Optional[ConversationEventStream] = None
    timeline: Optional[ConversationTimeline] = None

    # Pipeline State & Telemetry
    state: TimelinePipelineState = TimelinePipelineState.INITIALIZING
    stages_executed: List[str] = field(default_factory=list)
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Versioning & Lineage
    timeline_version: int = 1
    schema_version: str = "1.0.0"
    generator_version: str = "2.2.2"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0

    def transition_to(self, next_state: TimelinePipelineState) -> None:
        """Transitions pipeline state."""
        self.state = next_state

    def record_stage_execution(self, stage_name: str, duration_ms: float) -> None:
        """Records telemetry for an executed pipeline stage."""
        self.stages_executed.append(stage_name)
        self.stage_timings_ms[stage_name] = duration_ms

    def add_raw_event(self, event: TimelineEvent) -> None:
        """Appends a raw extracted timeline event."""
        self.raw_events.append(event)

    def add_raw_events(self, events: List[TimelineEvent]) -> None:
        """Appends multiple raw extracted timeline events."""
        self.raw_events.extend(events)

    def set_normalized_events(self, events: List[TimelineEvent]) -> None:
        """Sets normalized and ordered events."""
        self.normalized_events = list(events)

    def add_milestone(self, milestone: TimelineMilestone) -> None:
        """Appends a synthesized business milestone."""
        self.milestones.append(milestone)

    def add_important_moment(self, moment: ImportantMoment) -> None:
        """Appends a detected important moment."""
        self.important_moments.append(moment)

    def add_warning(self, message: str) -> None:
        """Logs a non-fatal warning."""
        self.warnings.append(message)

    def add_validation_error(self, message: str) -> None:
        """Logs a validation error."""
        self.validation_errors.append(message)
