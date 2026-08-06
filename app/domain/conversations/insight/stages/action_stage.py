"""
HunterOS Engage V1 - Detect Action Items Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.detectors.actions.registry import (
    ActionItemDetectorRegistry,
    default_action_item_detector_registry,
)
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class DetectActionItemsStage(InsightPipelineStage):
    """Executes action item detection algorithms across conversation artifacts."""

    def __init__(self, registry: Optional[ActionItemDetectorRegistry] = None) -> None:
        self.registry = registry or default_action_item_detector_registry

    @property
    def stage_name(self) -> str:
        return "DetectActionItemsStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.DETECTING_ACTION_ITEMS)
        detected_actions = self.registry.detect_all(context)
        context.raw_action_items = detected_actions
        logger.debug("Detected %d raw action items for %s", len(detected_actions), context.conversation_id)
