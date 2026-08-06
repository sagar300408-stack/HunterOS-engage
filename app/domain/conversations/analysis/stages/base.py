"""
HunterOS Engage — Pipeline Stage Base Interface (Phase 2.2.1)

Defines the abstract contract for independent, isolated, and replaceable
pipeline execution stages.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import PipelineState


class PipelineStage(ABC):
    """Abstract base class for all conversation analysis pipeline stages."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Human-readable identifier of this pipeline stage."""
        pass

    @property
    @abstractmethod
    def target_state(self) -> PipelineState:
        """The pipeline lifecycle state associated with this stage."""
        pass

    def run(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        """
        Executes the stage logic and records timing telemetry.
        """
        context.state = self.target_state
        start = time.perf_counter()
        try:
            context = self.execute(context)
        except Exception as ex:
            context.add_error(f"Stage [{self.stage_name}] failed: {str(ex)}")
            context.state = PipelineState.FAILED
            raise ex
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            context.add_stage_timing(self.stage_name, elapsed_ms)
        return context

    @abstractmethod
    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        """The core stage transformation logic reading and writing through context."""
        pass
