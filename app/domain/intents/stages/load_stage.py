"""
HunterOS Engage V1 - Load Artifacts Stage
Loads conversation intelligence artifacts into execution context.
"""

from __future__ import annotations

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.stages.base import IntentPipelineStage


class LoadArtifactsStage(IntentPipelineStage):
    """Verifies that at least one conversation intelligence artifact is present."""

    @property
    def stage_name(self) -> str:
        return "LoadArtifactsStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.LOADING

    def execute(self, context: IntentDetectionContext) -> None:
        if not (context.analysis_result or context.timeline or context.insight_result):
            context.add_warning("No Conversation Intelligence artifacts provided to IntentDetectionContext.")
