"""
HunterOS Engage V1 - Extract Events Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.extractors.registry import (
    TimelineEventExtractorRegistry,
    default_timeline_event_extractor_registry,
)
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class ExtractEventsStage(TimelinePipelineStage):
    """Orchestrates event extraction using the TimelineEventExtractorRegistry."""

    def __init__(self, registry: Optional[TimelineEventExtractorRegistry] = None) -> None:
        self.registry = registry or default_timeline_event_extractor_registry

    @property
    def stage_name(self) -> str:
        return "ExtractEventsStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.EXTRACTING_EVENTS)

        extracted_events = self.registry.extract_all(context)
        context.add_raw_events(extracted_events)

        logger.debug(
            "Extracted %d raw timeline events for conversation %s",
            len(extracted_events),
            context.conversation_id,
        )
