"""
HunterOS Engage V1 - Normalize Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.normalizer import (
    TimelineEventNormalizer,
    default_timeline_event_normalizer,
)
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class NormalizeTimelineEventsStage(TimelinePipelineStage):
    """Normalizes raw timeline events, deduplicates overlapping records, and standardizes categories."""

    def __init__(self, normalizer: Optional[TimelineEventNormalizer] = None) -> None:
        self.normalizer = normalizer or default_timeline_event_normalizer

    @property
    def stage_name(self) -> str:
        return "NormalizeTimelineEventsStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.NORMALIZING)

        normalized = self.normalizer.normalize(context.raw_events)
        context.set_normalized_events(normalized)

        logger.debug(
            "Normalized %d raw events into %d canonical events for conversation %s",
            len(context.raw_events),
            len(normalized),
            context.conversation_id,
        )
