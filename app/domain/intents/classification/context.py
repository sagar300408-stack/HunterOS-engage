"""
HunterOS Engage V1 - Intent Classification Context
Carries working state across the 8-stage classification pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ExtractedFact,
    TopicAnalysis,
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
from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.models import (
    ClassifiedIntent,
    IntentGroup,
    IntentRelationship,
)
from app.domain.intents.models import DetectedIntent, IntentDetectionResult


class IntentClassificationContext:
    """
    Mutable pipeline execution context holding input artifacts and working state.
    """

    def __init__(
        self,
        conversation_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        detected_intents: Optional[List[DetectedIntent]] = None,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        insight_result: Optional[ConversationInsightResult] = None,
        workspace_id: Optional[uuid.UUID] = None,
        customer_id: Optional[str] = None,
        active_plugins: Optional[List[str]] = None,
    ):
        self.conversation_id = conversation_id
        self.workspace_id = workspace_id
        self.customer_id = customer_id
        self.detection_result = detection_result
        self.raw_detected_intents: List[DetectedIntent] = (
            list(detected_intents)
            if detected_intents is not None
            else (list(detection_result.intents) if detection_result else [])
        )
        self.analysis_result = analysis_result
        self.timeline = timeline
        self.insight_result = insight_result
        self.active_plugins: List[str] = list(active_plugins) if active_plugins else []

        # Working state populated through pipeline stages
        self.loaded_intents: List[DetectedIntent] = []
        self.canonical_intents: List[CanonicalIntent] = []
        self.classified_intents: List[ClassifiedIntent] = []
        self.relationships: List[IntentRelationship] = []
        self.groups: List[IntentGroup] = []

        # Diagnostics & Timings
        self.executed_rules: List[str] = []
        self.matched_rules: List[str] = []
        self.rejected_rules: List[str] = []
        self.applied_plugins: List[str] = []
        self.applied_rule_packs: List[str] = []
        self.validation_warnings: List[str] = []
        self.validation_errors: List[str] = []
        self.stage_timings: Dict[str, float] = {}

    # ── Upstream Artifact Accessors ──────────────────────────────────────────

    def get_events(self) -> List[TimelineEvent]:
        if self.timeline and self.timeline.event_stream:
            return self.timeline.event_stream.events
        return []

    def get_milestones(self) -> List[TimelineMilestone]:
        if self.timeline:
            return self.timeline.milestones
        return []

    def get_moments(self) -> List[ImportantMoment]:
        if self.timeline:
            return self.timeline.important_moments
        return []

    def get_facts(self) -> List[ExtractedFact]:
        if self.analysis_result:
            return self.analysis_result.facts
        return []

    def get_topics(self) -> Optional[TopicAnalysis]:
        if self.analysis_result:
            return self.analysis_result.topics
        return None

    def get_actions(self) -> List[ActionItemInsight]:
        if self.insight_result:
            return self.insight_result.actions
        return []

    def get_risks(self) -> List[RiskInsight]:
        if self.insight_result:
            return self.insight_result.risks
        return []

    def get_opportunities(self) -> List[OpportunityInsight]:
        if self.insight_result:
            return self.insight_result.opportunities
        return []

    # ── State Helpers ─────────────────────────────────────────────────────────

    def get_canonical_by_original_id(self, original_id: uuid.UUID) -> Optional[CanonicalIntent]:
        for c in self.canonical_intents:
            if c.original_intent_id == original_id:
                return c
        return None

    def get_classified_by_original_id(self, original_id: uuid.UUID) -> Optional[ClassifiedIntent]:
        for ci in self.classified_intents:
            if ci.original_intent_id == original_id:
                return ci
        return None

    def get_classified_by_id(self, classified_id: uuid.UUID) -> Optional[ClassifiedIntent]:
        for ci in self.classified_intents:
            if ci.classified_intent_id == classified_id:
                return ci
        return None

    def add_warning(self, msg: str) -> None:
        self.validation_warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.validation_errors.append(msg)

    def record_stage_timing(self, stage_name: str, duration_ms: float) -> None:
        self.stage_timings[stage_name] = round(duration_ms, 3)
