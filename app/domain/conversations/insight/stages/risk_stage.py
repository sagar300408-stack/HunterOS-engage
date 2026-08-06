"""
HunterOS Engage V1 - Detect Risks Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.detectors.risks.registry import (
    RiskDetectorRegistry,
    default_risk_detector_registry,
)
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class DetectRisksStage(InsightPipelineStage):
    """Executes risk detection algorithms across conversation artifacts."""

    def __init__(self, registry: Optional[RiskDetectorRegistry] = None) -> None:
        self.registry = registry or default_risk_detector_registry

    @property
    def stage_name(self) -> str:
        return "DetectRisksStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.DETECTING_RISKS)
        detected_risks = self.registry.detect_all(context)
        context.raw_risks = detected_risks
        logger.debug("Detected %d raw risks for %s", len(detected_risks), context.conversation_id)
