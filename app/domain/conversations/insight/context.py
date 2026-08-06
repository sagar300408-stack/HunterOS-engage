"""
HunterOS Engage V1 - Conversation Insight Execution Context
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines pipeline state machine and shared mutable execution context
passed through pipeline stages during deterministic insight generation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ExtractedFact,
    TopicAnalysis,
)
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ConversationInsight,
    ConversationInsightResult,
    InsightScopeType,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.timeline.models import (
    ConversationTimeline,
    ImportantMoment,
    TimelineEvent,
    TimelineMilestone,
)

logger = logging.getLogger(__name__)


class InsightPipelineState(str, Enum):
    """Execution state transitions for the insight pipeline."""
    INITIALIZED = "INITIALIZED"
    LOADING = "LOADING"
    NORMALIZING = "NORMALIZING"
    DETECTING_RISKS = "DETECTING_RISKS"
    DETECTING_OPPORTUNITIES = "DETECTING_OPPORTUNITIES"
    DETECTING_ACTION_ITEMS = "DETECTING_ACTION_ITEMS"
    CLASSIFYING = "CLASSIFYING"
    VALIDATING = "VALIDATING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ConversationInsightContext:
    """
    Mutable state container and accumulator for the 8-stage insight pipeline.
    Carries source artifacts and intermediate candidate insights.
    """
    # ── Source Inputs ─────────────────────────────────────────────────────────
    analysis_result: Optional[ConversationAnalysisResult] = None
    timeline: Optional[ConversationTimeline] = None
    conversation_id: str = ""
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    scope_type: InsightScopeType = InsightScopeType.CONVERSATION

    # ── Pipeline State ────────────────────────────────────────────────────────
    state: InsightPipelineState = InsightPipelineState.INITIALIZED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Detected Raw Candidates ───────────────────────────────────────────────
    raw_risks: List[RiskInsight] = field(default_factory=list)
    raw_opportunities: List[OpportunityInsight] = field(default_factory=list)
    raw_action_items: List[ActionItemInsight] = field(default_factory=list)

    # ── Classified & Normalized Insights ──────────────────────────────────────
    classified_risks: List[RiskInsight] = field(default_factory=list)
    classified_opportunities: List[OpportunityInsight] = field(default_factory=list)
    classified_action_items: List[ActionItemInsight] = field(default_factory=list)
    all_insights: List[ConversationInsight] = field(default_factory=list)

    # ── Diagnostics & Telemetry ───────────────────────────────────────────────
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    stages_executed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True

    # ── Final Output ──────────────────────────────────────────────────────────
    result: Optional[ConversationInsightResult] = None

    def __post_init__(self) -> None:
        if self.analysis_result and not self.conversation_id:
            self.conversation_id = self.analysis_result.conversation_id
        elif self.timeline and not self.conversation_id:
            self.conversation_id = self.timeline.conversation_id

        if self.analysis_result and not self.workspace_id:
            self.workspace_id = self.analysis_result.workspace_id
        elif self.timeline and not self.workspace_id:
            self.workspace_id = self.timeline.workspace_id

    @property
    def current_state(self) -> InsightPipelineState:
        """Returns the current pipeline execution state."""
        return self.state

    def transition_to(self, target_state: InsightPipelineState) -> None:
        """Transitions pipeline to next state with logging."""
        logger.debug(
            "InsightContext transition: %s -> %s (conv_id=%s)",
            self.state.value,
            target_state.value,
            self.conversation_id,
        )
        self.state = target_state

    def record_stage_execution(self, stage_name: str, duration_ms: float) -> None:
        """Records execution timestamp and duration for diagnostics."""
        self.stages_executed.append(stage_name)
        self.stage_timings_ms[stage_name] = round(duration_ms, 3)

    def add_warning(self, message: str) -> None:
        """Records a non-fatal warning during execution."""
        logger.warning("Insight warning [%s]: %s", self.conversation_id, message)
        self.warnings.append(message)

    def add_validation_error(self, error: str) -> None:
        """Records a validation failure."""
        logger.error("Insight validation error [%s]: %s", self.conversation_id, error)
        self.validation_errors.append(error)
        self.is_valid = False

    # ── Helper Query Methods ──────────────────────────────────────────────────

    def get_events(self) -> List[TimelineEvent]:
        """Returns all events from timeline if available."""
        if self.timeline and self.timeline.event_stream:
            return self.timeline.event_stream.events
        return []

    def get_milestones(self) -> List[TimelineMilestone]:
        """Returns all milestones from timeline if available."""
        if self.timeline:
            return self.timeline.milestones
        return []

    def get_moments(self) -> List[ImportantMoment]:
        """Returns all important moments from timeline if available."""
        if self.timeline:
            return self.timeline.important_moments
        return []

    def get_facts(self) -> List[ExtractedFact]:
        """Returns all extracted facts from analysis result."""
        if self.analysis_result:
            return self.analysis_result.facts or []
        return []

    def get_segments(self) -> List[ConversationSegment]:
        """Returns all conversation segments from analysis result."""
        if self.analysis_result:
            return self.analysis_result.segments or []
        return []

    def get_topics(self) -> Optional[TopicAnalysis]:
        """Returns topic analysis from analysis result."""
        if self.analysis_result:
            return self.analysis_result.topics
        return None

    def get_metadata(self) -> Optional[ConversationMetadata]:
        """Returns conversation metadata from analysis result."""
        if self.analysis_result:
            return self.analysis_result.metadata
        return None
