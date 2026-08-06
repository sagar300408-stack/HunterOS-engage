"""
HunterOS Engage V1 - Validate Timeline Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import TimelinePipelineState
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage
from app.domain.conversations.timeline.validation import (
    TimelineValidationFramework,
    default_timeline_validation_framework,
)

logger = logging.getLogger(__name__)


class ValidateTimelineStage(TimelinePipelineStage):
    """Executes TimelineValidationFramework to ensure structural and invariant correctness."""

    def __init__(self, validator: Optional[TimelineValidationFramework] = None) -> None:
        self.validator = validator or default_timeline_validation_framework

    @property
    def stage_name(self) -> str:
        return "ValidateTimelineStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.VALIDATING)

        errors = self.validator.validate(context, raise_on_error=False)
        if errors:
            logger.warning(
                "Timeline validation produced %d warnings/errors for conversation %s",
                len(errors),
                context.conversation_id,
            )
