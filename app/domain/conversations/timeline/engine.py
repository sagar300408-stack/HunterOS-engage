"""
HunterOS Engage V1 - Conversation Timeline Engine
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

High-performance orchestrator for timeline construction, milestone detection,
moment extraction, and multi-view projection rendering.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.extractors.registry import (
    TimelineEventExtractorRegistry,
    default_timeline_event_extractor_registry,
)
from app.domain.conversations.timeline.milestones.registry import (
    MilestoneRuleRegistry,
    default_milestone_rule_registry,
)
from app.domain.conversations.timeline.models import (
    ConversationTimeline,
    TimelinePipelineState,
    TimelineScopeType,
)
from app.domain.conversations.timeline.moments.registry import (
    ImportantMomentRegistry,
    default_important_moment_registry,
)
from app.domain.conversations.timeline.normalizer import (
    TimelineEventNormalizer,
    default_timeline_event_normalizer,
)
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage
from app.domain.conversations.timeline.stages.extract_events_stage import ExtractEventsStage
from app.domain.conversations.timeline.stages.load_stage import LoadAnalysisStage
from app.domain.conversations.timeline.stages.milestone_stage import DetectMilestonesStage
from app.domain.conversations.timeline.stages.moment_stage import DetectImportantMomentsStage
from app.domain.conversations.timeline.stages.normalize_stage import NormalizeTimelineEventsStage
from app.domain.conversations.timeline.stages.ordering_stage import ChronologicalOrderingStage
from app.domain.conversations.timeline.stages.output_stage import OutputTimelineStage
from app.domain.conversations.timeline.stages.validation_stage import ValidateTimelineStage
from app.domain.conversations.timeline.validation import (
    TimelineValidationFramework,
    default_timeline_validation_framework,
)
from app.domain.conversations.timeline.views.registry import (
    TimelineViewRegistry,
    default_timeline_view_registry,
)

logger = logging.getLogger(__name__)


class ConversationTimelineEngine:
    """Orchestrates end-to-end timeline construction from conversation analysis artifacts."""

    def __init__(
        self,
        extractor_registry: Optional[TimelineEventExtractorRegistry] = None,
        milestone_registry: Optional[MilestoneRuleRegistry] = None,
        moment_registry: Optional[ImportantMomentRegistry] = None,
        view_registry: Optional[TimelineViewRegistry] = None,
        normalizer: Optional[TimelineEventNormalizer] = None,
        validator: Optional[TimelineValidationFramework] = None,
    ) -> None:
        self.extractor_registry = extractor_registry or default_timeline_event_extractor_registry
        self.milestone_registry = milestone_registry or default_milestone_rule_registry
        self.moment_registry = moment_registry or default_important_moment_registry
        self.view_registry = view_registry or default_timeline_view_registry
        self.normalizer = normalizer or default_timeline_event_normalizer
        self.validator = validator or default_timeline_validation_framework

        self._stages: List[TimelinePipelineStage] = [
            LoadAnalysisStage(),
            ExtractEventsStage(self.extractor_registry),
            NormalizeTimelineEventsStage(self.normalizer),
            ChronologicalOrderingStage(),
            DetectMilestonesStage(self.milestone_registry),
            DetectImportantMomentsStage(self.moment_registry),
            ValidateTimelineStage(self.validator),
            OutputTimelineStage(),
        ]

    def build_timeline(
        self,
        analysis_result: ConversationAnalysisResult,
        scope_type: TimelineScopeType = TimelineScopeType.CONVERSATION,
        timeline_version: int = 1,
        **kwargs: Any,
    ) -> ConversationTimeline:
        """Constructs an immutable ConversationTimeline aggregate root from ConversationAnalysisResult."""
        context = ConversationTimelineContext(
            analysis_result=analysis_result,
            conversation_id=analysis_result.conversation_id,
            workspace_id=analysis_result.workspace_id,
            customer_id=kwargs.get("customer_id"),
            scope_type=scope_type,
            timeline_version=timeline_version,
        )

        for stage in self._stages:
            t0 = time.perf_counter()
            try:
                stage.execute(context)
            except Exception as e:
                logger.error("Stage %s failed: %s", stage.stage_name, str(e), exc_info=True)
                context.add_validation_error(f"Stage {stage.stage_name} crashed: {str(e)}")
                context.transition_to(TimelinePipelineState.FAILED)
                raise
            finally:
                t1 = time.perf_counter()
                elapsed_ms = (t1 - t0) * 1000.0
                context.record_stage_execution(stage.stage_name, elapsed_ms)

        if not context.timeline:
            raise RuntimeError("Pipeline failed to synthesize ConversationTimeline output.")

        return context.timeline

    def render_view(
        self,
        timeline: ConversationTimeline,
        view_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Renders the timeline into a specific projection view using the TimelineViewRegistry."""
        return self.view_registry.render_view(view_name, timeline, **kwargs)

    def validate_timeline(self, timeline: ConversationTimeline) -> List[str]:
        """Validates a timeline aggregate root directly."""
        context = ConversationTimelineContext(
            conversation_id=timeline.conversation_id,
            workspace_id=timeline.workspace_id,
            customer_id=timeline.customer_id,
            scope_type=timeline.scope_type,
            normalized_events=timeline.event_stream.events if timeline.event_stream else [],
            milestones=timeline.milestones,
            important_moments=timeline.important_moments,
            timeline_version=timeline.timeline_version,
        )
        return self.validator.validate(context, raise_on_error=False)


# Global default singleton instance
default_conversation_timeline_engine = ConversationTimelineEngine()
