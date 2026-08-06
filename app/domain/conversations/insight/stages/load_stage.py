"""
HunterOS Engage V1 - Load Artifacts Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class LoadArtifactsStage(InsightPipelineStage):
    """Verifies that required upstream analysis or timeline artifacts are present."""

    @property
    def stage_name(self) -> str:
        return "LoadArtifactsStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.LOADING)

        if not context.analysis_result and not context.timeline:
            raise ValueError("ConversationInsightContext requires at least one of ConversationAnalysisResult or ConversationTimeline.")

        if not context.conversation_id:
            if context.analysis_result:
                context.conversation_id = context.analysis_result.conversation_id
            elif context.timeline:
                context.conversation_id = context.timeline.conversation_id

        logger.debug("Loaded artifacts for conversation %s", context.conversation_id)
