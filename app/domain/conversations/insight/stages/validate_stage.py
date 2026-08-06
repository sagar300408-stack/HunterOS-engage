"""
HunterOS Engage V1 - Validate Insights Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.stages.base import InsightPipelineStage
from app.domain.conversations.insight.validation import (
    InsightValidationFramework,
    default_insight_validation_framework,
)

logger = logging.getLogger(__name__)


class ValidateInsightsStage(InsightPipelineStage):
    """Enforces evidence completeness, deduplication, reference integrity, and boundary guards."""

    def __init__(self, validator: Optional[InsightValidationFramework] = None) -> None:
        self.validator = validator or default_insight_validation_framework

    @property
    def stage_name(self) -> str:
        return "ValidateInsightsStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.VALIDATING)

        # Deduplicate first
        self.validator.deduplicate_insights(context)

        # Validate structural & boundary invariants
        errors = self.validator.validate_context(context)
        for err in errors:
            context.add_validation_error(err)

        if errors:
            logger.warning(
                "Insight validation encountered %d errors for conversation %s: %s",
                len(errors),
                context.conversation_id,
                errors,
            )
