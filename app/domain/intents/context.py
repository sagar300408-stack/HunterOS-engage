"""
HunterOS Engage V1 - Intent Detection Context & State Machine
Mutable accumulator and lifecycle state tracker for the intent detection pipeline.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ExtractedFact,
    TopicDistribution,
)
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ConversationInsightResult,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.timeline.models import (
    ConversationTimeline,
    ImportantMoment,
    TimelineEvent,
    TimelineMilestone,
)
from app.domain.intents.models import (
    DetectedIntent,
    IntentDetectionResult,
    RuleExecutionReport,
)


class IntentPipelineState(str, enum.Enum):
    """Lifecycle states of the Intent Detection Pipeline."""
    INITIALIZED = "INITIALIZED"
    LOADING = "LOADING"
    NORMALIZING = "NORMALIZING"
    RECOGNIZING = "RECOGNIZING"
    VALIDATING = "VALIDATING"
    RESOLVING = "RESOLVING"
    RESULT_GENERATION = "RESULT_GENERATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class IntentDetectionContext:
    """
    Mutable state container passed through each pipeline stage.
    Accumulates raw candidates, validated items, deduplicated items, telemetry and diagnostics.
    """
    # ── Ingested Artifacts ──────────────────────────────────────────────────
    analysis_result: Optional[ConversationAnalysisResult] = None
    timeline: Optional[ConversationTimeline] = None
    insight_result: Optional[ConversationInsightResult] = None

    # ── Identified Context ──────────────────────────────────────────────────
    conversation_id: str = ""
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None

    # ── Pipeline Progression State ──────────────────────────────────────────
    state: IntentPipelineState = IntentPipelineState.INITIALIZED
    candidate_intents: List[DetectedIntent] = field(default_factory=list)
    validated_intents: List[DetectedIntent] = field(default_factory=list)
    resolved_intents: List[DetectedIntent] = field(default_factory=list)

    # ── Execution Telemetry & Diagnostics ───────────────────────────────────
    start_time: float = field(default_factory=time.perf_counter)
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    stages_executed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    rule_execution_report: RuleExecutionReport = field(default_factory=RuleExecutionReport)
    is_valid: bool = True

    # ── Final Output Aggregate ──────────────────────────────────────────────
    result: Optional[IntentDetectionResult] = None

    # ── Properties & Lifecycle ──────────────────────────────────────────────

    @property
    def current_state(self) -> IntentPipelineState:
        return self.state

    def transition_to(self, new_state: IntentPipelineState) -> None:
        """Transitions state machine to the new stage."""
        self.state = new_state
        if new_state.value not in self.stages_executed:
            self.stages_executed.append(new_state.value)

    def record_stage_timing(self, stage_name: str, duration_ms: float) -> None:
        """Records execution duration in milliseconds for a specific stage."""
        self.stage_timings_ms[stage_name] = round(duration_ms, 3)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_validation_error(self, message: str) -> None:
        self.validation_errors.append(message)
        self.is_valid = False

    # ── Convenience Accessors for Detection Rules ───────────────────────────

    def get_facts(self) -> List[ExtractedFact]:
        if self.analysis_result and hasattr(self.analysis_result, "facts"):
            return list(self.analysis_result.facts)
        return []

    def get_topics(self) -> List[Any]:
        if self.analysis_result and hasattr(self.analysis_result, "topics"):
            topics_obj = self.analysis_result.topics
            if hasattr(topics_obj, "distribution"):
                return list(topics_obj.distribution)
            elif isinstance(topics_obj, list):
                return list(topics_obj)
        return []

    def get_events(self) -> List[TimelineEvent]:
        if self.timeline and hasattr(self.timeline, "events"):
            return list(self.timeline.events)
        return []

    def get_milestones(self) -> List[TimelineMilestone]:
        if self.timeline and hasattr(self.timeline, "milestones"):
            return list(self.timeline.milestones)
        return []

    def get_moments(self) -> List[ImportantMoment]:
        if self.timeline and hasattr(self.timeline, "moments"):
            return list(self.timeline.moments)
        return []

    def get_risks(self) -> List[RiskInsight]:
        if self.insight_result and hasattr(self.insight_result, "risks"):
            return list(self.insight_result.risks)
        return []

    def get_opportunities(self) -> List[OpportunityInsight]:
        if self.insight_result and hasattr(self.insight_result, "opportunities"):
            return list(self.insight_result.opportunities)
        return []

    def get_actions(self) -> List[ActionItemInsight]:
        if self.insight_result and hasattr(self.insight_result, "action_items"):
            return list(self.insight_result.action_items)
        return []
