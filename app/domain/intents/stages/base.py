"""
HunterOS Engage V1 - Abstract Intent Pipeline Stage Base
"""

from __future__ import annotations

import abc
import time

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState


class IntentPipelineStage(abc.ABC):
    """Abstract base class for a linear deterministic stage in the Intent Detection Pipeline."""

    @property
    @abc.abstractmethod
    def stage_name(self) -> str:
        """Name of the pipeline stage."""
        pass

    @property
    @abc.abstractmethod
    def target_state(self) -> IntentPipelineState:
        """Pipeline state this stage transitions context into."""
        pass

    def run(self, context: IntentDetectionContext) -> None:
        """Execute stage logic with timing instrumentation."""
        context.transition_to(self.target_state)
        start = time.perf_counter()
        try:
            self.execute(context)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            context.record_stage_timing(self.stage_name, duration_ms)

    @abc.abstractmethod
    def execute(self, context: IntentDetectionContext) -> None:
        """Stage execution logic."""
        pass
