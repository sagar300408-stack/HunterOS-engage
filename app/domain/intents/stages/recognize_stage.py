"""
HunterOS Engage V1 - Recognize Candidates Stage
Orchestrates candidate intent detection through the IntentRecognizer.
"""

from __future__ import annotations

from typing import Optional

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.recognizer import IntentRecognizer
from app.domain.intents.stages.base import IntentPipelineStage


class RecognizeCandidatesStage(IntentPipelineStage):
    """Executes intent recognition across registered rule packs / providers."""

    def __init__(self, recognizer: Optional[IntentRecognizer] = None):
        self._recognizer = recognizer or IntentRecognizer()

    @property
    def stage_name(self) -> str:
        return "RecognizeCandidatesStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.RECOGNIZING

    def execute(self, context: IntentDetectionContext) -> None:
        candidates, report = self._recognizer.recognize(context)
        context.candidate_intents = candidates
        context.rule_execution_report = report
