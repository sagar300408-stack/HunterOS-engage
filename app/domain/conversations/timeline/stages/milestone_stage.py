"""
HunterOS Engage V1 - Detect Milestones Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.milestones.registry import (
    MilestoneRuleRegistry,
    default_milestone_rule_registry,
)
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class DetectMilestonesStage(TimelinePipelineStage):
    """Detects business milestones using the MilestoneRuleRegistry."""

    def __init__(self, registry: Optional[MilestoneRuleRegistry] = None) -> None:
        self.registry = registry or default_milestone_rule_registry

    @property
    def stage_name(self) -> str:
        return "DetectMilestonesStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.DETECTING_MILESTONES)

        detected_milestones = self.registry.evaluate_all(context)
        for ms in detected_milestones:
            context.add_milestone(ms)

        logger.debug(
            "Detected %d business milestones for conversation %s",
            len(detected_milestones),
            context.conversation_id,
        )
