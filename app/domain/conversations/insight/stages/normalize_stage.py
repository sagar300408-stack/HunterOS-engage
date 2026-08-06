"""
HunterOS Engage V1 - Normalize Inputs Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class NormalizeInputsStage(InsightPipelineStage):
    """Aligns identifiers, validates metadata completeness, and prepares data structures."""

    @property
    def stage_name(self) -> str:
        return "NormalizeInputsStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.NORMALIZING)

        if context.analysis_result and not context.workspace_id:
            context.workspace_id = context.analysis_result.workspace_id
        elif context.timeline and not context.workspace_id:
            context.workspace_id = context.timeline.workspace_id

        if context.analysis_result and not context.customer_id:
            context.customer_id = getattr(context.analysis_result, "customer_id", None)
        if not context.customer_id and context.timeline:
            context.customer_id = context.timeline.customer_id

        logger.debug(
            "Normalized inputs for conv=%s, ws=%s, cust=%s",
            context.conversation_id,
            context.workspace_id,
            context.customer_id,
        )
