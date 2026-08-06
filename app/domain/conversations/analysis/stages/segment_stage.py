"""
HunterOS Engage — Segment Stage (Phase 2.2.1)

Segments normalized messages into conversational phases.
"""

from __future__ import annotations

from typing import Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.segmentation import (
    ConversationSegmentationEngine,
)
from app.domain.conversations.analysis.stages.base import PipelineStage


class SegmentStage(PipelineStage):
    """Pipeline stage executing conversation segmentation."""

    def __init__(self, engine: Optional[ConversationSegmentationEngine] = None) -> None:
        self._engine = engine or ConversationSegmentationEngine()

    @property
    def stage_name(self) -> str:
        return "SegmentStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.SEGMENTING

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        context.segments = self._engine.segment(context.normalized_messages)
        return context
