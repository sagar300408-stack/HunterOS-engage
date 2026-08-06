"""
HunterOS Engage — Output Stage (Phase 2.2.1)

Finalizes pipeline execution and transitions context to completed state.
"""

from __future__ import annotations

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage


class OutputStage(PipelineStage):
    """Pipeline stage finalizing outputs and diagnostics."""

    @property
    def stage_name(self) -> str:
        return "OutputStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.COMPLETED

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        context.state = PipelineState.COMPLETED
        return context
