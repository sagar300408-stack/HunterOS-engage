"""
HunterOS Engage V1 - Detect Important Moments Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.moments.registry import (
    ImportantMomentRegistry,
    default_important_moment_registry,
)
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class DetectImportantMomentsStage(TimelinePipelineStage):
    """Detects high-value conversational moments using the ImportantMomentRegistry."""

    def __init__(self, registry: Optional[ImportantMomentRegistry] = None) -> None:
        self.registry = registry or default_important_moment_registry

    @property
    def stage_name(self) -> str:
        return "DetectImportantMomentsStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.DETECTING_MOMENTS)

        detected_moments = self.registry.evaluate_all(context)
        for mom in detected_moments:
            context.add_important_moment(mom)

        logger.debug(
            "Detected %d important moments for conversation %s",
            len(detected_moments),
            context.conversation_id,
        )
