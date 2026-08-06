"""
HunterOS Engage V1 - Output Timeline Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import (
    ConversationEventStream,
    ConversationTimeline,
    TimelineDiagnostics,
    TimelineMetadata,
    TimelinePipelineState,
)
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class OutputTimelineStage(TimelinePipelineStage):
    """Compiles the immutable ConversationEventStream and ConversationTimeline aggregate root."""

    @property
    def stage_name(self) -> str:
        return "OutputTimelineStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.COMPLETED)

        events = list(context.normalized_events)
        start_time = events[0].occurred_at if events else None
        end_time = events[-1].occurred_at if events else None
        duration_s = (end_time - start_time).total_seconds() if (start_time and end_time) else 0.0

        # Event stream
        stream = ConversationEventStream(
            stream_id=uuid.uuid4(),
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            events=events,
            start_time=start_time,
            end_time=end_time,
        )
        context.event_stream = stream

        # Category distribution
        cat_counts = Counter(e.category.value for e in events)

        # Metadata
        metadata = TimelineMetadata(
            timeline_id=uuid.uuid4(),
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            scope_type=context.scope_type,
            total_events=len(events),
            total_milestones=len(context.milestones),
            total_moments=len(context.important_moments),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=round(max(0.0, duration_s), 3),
            event_category_distribution=dict(cat_counts),
            timeline_version=context.timeline_version,
            schema_version=context.schema_version,
            generator_version=context.generator_version,
            generated_at=datetime.now(timezone.utc),
        )

        # Diagnostics
        stages = list(context.stages_executed)
        if self.stage_name not in stages:
            stages.append(self.stage_name)

        total_time_ms = sum(context.stage_timings_ms.values())
        diagnostics = TimelineDiagnostics(
            pipeline_execution_time_ms=round(total_time_ms, 3),
            stage_timings_ms=dict(context.stage_timings_ms),
            stages_executed=stages,
            warnings=list(context.warnings),
            validation_errors=list(context.validation_errors),
            is_valid=context.is_valid,
        )

        # Aggregate Root
        timeline = ConversationTimeline(
            timeline_id=metadata.timeline_id,
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            scope_type=context.scope_type,
            metadata=metadata,
            event_stream=stream,
            milestones=list(context.milestones),
            important_moments=list(context.important_moments),
            diagnostics=diagnostics,
            timeline_version=context.timeline_version,
            created_at=datetime.now(timezone.utc),
        )
        context.timeline = timeline

        logger.debug(
            "Synthesized ConversationTimeline %s for conversation %s (%d events, %d milestones, %d moments)",
            timeline.timeline_id,
            context.conversation_id,
            len(events),
            len(context.milestones),
            len(context.important_moments),
        )
