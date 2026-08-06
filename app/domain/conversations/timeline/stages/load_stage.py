"""
HunterOS Engage V1 - Load Analysis Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class LoadAnalysisStage(TimelinePipelineStage):
    """Loads and validates conversation analysis results into context."""

    @property
    def stage_name(self) -> str:
        return "LoadAnalysisStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.LOADING)

        if not context.analysis_result:
            msg = "Missing ConversationAnalysisResult in timeline context."
            context.add_validation_error(msg)
            context.transition_to(TimelinePipelineState.FAILED)
            raise ValueError(msg)

        res = context.analysis_result
        if not context.conversation_id:
            context.conversation_id = res.conversation_id
        if not context.workspace_id:
            context.workspace_id = res.workspace_id

        logger.debug("Loaded analysis result for conversation: %s", context.conversation_id)
