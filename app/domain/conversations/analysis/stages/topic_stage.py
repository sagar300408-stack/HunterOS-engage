"""
HunterOS Engage — Topic Stage (Phase 2.2.1)

Detects hierarchical topics, distributions, and progression timelines.
"""

from __future__ import annotations

from typing import Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.engines import TopicDetectionEngine
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage


class TopicStage(PipelineStage):
    """Pipeline stage executing topic detection and timeline generation."""

    def __init__(self, engine: Optional[TopicDetectionEngine] = None) -> None:
        self._engine = engine or TopicDetectionEngine()

    @property
    def stage_name(self) -> str:
        return "TopicStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.DETECTING_TOPICS

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        context.topics = self._engine.detect_topics(context.normalized_messages, context=context)
        return context
