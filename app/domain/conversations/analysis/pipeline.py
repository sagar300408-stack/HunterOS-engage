"""
HunterOS Engage — Conversation Pipeline Runner (Phase 2.2.1)

Chains and executes independent pipeline stages sequentially on the
ConversationAnalysisContext to produce the final ConversationAnalysisResult aggregate.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    PipelineState,
)
from app.domain.conversations.analysis.stages.base import PipelineStage
from app.domain.conversations.analysis.stages.fact_extraction_stage import (
    FactExtractionStage,
)
from app.domain.conversations.analysis.stages.fact_normalization_stage import (
    FactNormalizationStage,
)
from app.domain.conversations.analysis.stages.load_stage import LoadStage
from app.domain.conversations.analysis.stages.normalize_stage import (
    NormalizeStage,
)
from app.domain.conversations.analysis.stages.output_stage import OutputStage
from app.domain.conversations.analysis.stages.segment_stage import SegmentStage
from app.domain.conversations.analysis.stages.summary_stage import SummaryStage
from app.domain.conversations.analysis.stages.topic_stage import TopicStage
from app.domain.conversations.analysis.stages.validation_stage import (
    ValidationStage,
)

logger = logging.getLogger("hunteros.conversations.analysis.pipeline")


class ConversationPipelineRunner:
    """
    Executes a sequence of independent PipelineStages against a ConversationAnalysisContext.
    """

    def __init__(self, stages: Optional[List[PipelineStage]] = None) -> None:
        if stages is not None:
            self._stages = list(stages)
        else:
            self._stages = self._build_default_stages()

    def _build_default_stages(self) -> List[PipelineStage]:
        """Assembles standard 9-stage deterministic pipeline."""
        return [
            LoadStage(),
            NormalizeStage(),
            SegmentStage(),
            TopicStage(),
            FactExtractionStage(),
            FactNormalizationStage(),
            SummaryStage(),
            ValidationStage(),
            OutputStage(),
        ]

    @property
    def stages(self) -> List[PipelineStage]:
        return list(self._stages)

    def add_stage(self, stage: PipelineStage, index: Optional[int] = None) -> None:
        """Insert or append a stage into the pipeline."""
        if index is not None:
            self._stages.insert(index, stage)
        else:
            self._stages.append(stage)

    def replace_stage(self, stage_name: str, new_stage: PipelineStage) -> bool:
        """Replace an existing stage by name."""
        for idx, stg in enumerate(self._stages):
            if stg.stage_name.lower() == stage_name.lower():
                self._stages[idx] = new_stage
                return True
        return False

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisResult:
        """
        Sequentially executes all configured stages on context and returns the aggregate root.
        """
        for stage in self._stages:
            try:
                context = stage.run(context)
            except Exception as e:
                logger.error(f"Pipeline failure at stage [{stage.stage_name}]: {e}")
                context.state = PipelineState.FAILED
                context.add_error(f"Stage failure: {str(e)}")
                break

        return context.build_result()
