"""
HunterOS Engage — Fact Extraction Stage (Phase 2.2.1)

Extracts structured key facts from normalized conversation messages.
"""

from __future__ import annotations

from typing import Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.engines import KeyFactExtractionEngine
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage


class FactExtractionStage(PipelineStage):
    """Pipeline stage executing multi-category key fact extraction."""

    def __init__(self, engine: Optional[KeyFactExtractionEngine] = None) -> None:
        self._engine = engine or KeyFactExtractionEngine()

    @property
    def stage_name(self) -> str:
        return "FactExtractionStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.EXTRACTING_FACTS

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        context.facts = self._engine.extract_facts(context.normalized_messages, context=context)
        return context
