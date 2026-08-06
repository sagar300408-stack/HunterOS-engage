"""
HunterOS Engage V1 - Classify Insights Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.conversations.insight.classification import (
    InsightClassifier,
    default_insight_classifier,
)
from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class ClassifyInsightsStage(InsightPipelineStage):
    """Harmonizes candidate insights into standardized entities with unified priority evaluation."""

    def __init__(self, classifier: Optional[InsightClassifier] = None) -> None:
        self.classifier = classifier or default_insight_classifier

    @property
    def stage_name(self) -> str:
        return "ClassifyInsightsStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.CLASSIFYING)
        self.classifier.classify_and_harmonize(context)
        logger.debug("Classified all insights for %s", context.conversation_id)
