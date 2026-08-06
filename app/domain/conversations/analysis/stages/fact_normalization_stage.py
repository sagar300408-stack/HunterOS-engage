"""
HunterOS Engage — Fact Normalization Stage (Phase 2.2.1)

Standardizes extracted facts into canonical representations.
"""

from __future__ import annotations

from typing import List, Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import (
    ExtractedFact,
    PipelineState,
)
from app.domain.conversations.analysis.normalizer import (
    FactNormalizer,
    default_fact_normalizer,
)
from app.domain.conversations.analysis.stages.base import PipelineStage


class FactNormalizationStage(PipelineStage):
    """Pipeline stage executing canonical transformation on all extracted facts."""

    def __init__(self, normalizer: Optional[FactNormalizer] = None) -> None:
        self._normalizer = normalizer or default_fact_normalizer

    @property
    def stage_name(self) -> str:
        return "FactNormalizationStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.NORMALIZING_FACTS

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        normalized_facts: List[ExtractedFact] = []
        for fact in context.facts:
            norm_fact = self._normalizer.normalize(fact)
            normalized_facts.append(norm_fact)

        context.facts = normalized_facts
        return context
