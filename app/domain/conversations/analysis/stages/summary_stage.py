"""
HunterOS Engage — Summary Stage (Phase 2.2.1)

Generates multi-perspective deterministic summaries from analysis context.
"""

from __future__ import annotations

from typing import Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.engines import ConversationSummaryEngine
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage


class SummaryStage(PipelineStage):
    """Pipeline stage executing multi-perspective summary generation."""

    def __init__(self, engine: Optional[ConversationSummaryEngine] = None) -> None:
        self._engine = engine or ConversationSummaryEngine()

    @property
    def stage_name(self) -> str:
        return "SummaryStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.SUMMARIZING

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        context.summaries = self._engine.generate_summaries(context)
        return context
