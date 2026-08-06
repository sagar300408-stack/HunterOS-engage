"""
HunterOS Engage V1 - Detect Opportunities Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.detectors.opportunities.registry import (
    OpportunityDetectorRegistry,
    default_opportunity_detector_registry,
)
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class DetectOpportunitiesStage(InsightPipelineStage):
    """Executes opportunity detection algorithms across conversation artifacts."""

    def __init__(self, registry: Optional[OpportunityDetectorRegistry] = None) -> None:
        self.registry = registry or default_opportunity_detector_registry

    @property
    def stage_name(self) -> str:
        return "DetectOpportunitiesStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.DETECTING_OPPORTUNITIES)
        detected_opps = self.registry.detect_all(context)
        context.raw_opportunities = detected_opps
        logger.debug("Detected %d raw opportunities for %s", len(detected_opps), context.conversation_id)
