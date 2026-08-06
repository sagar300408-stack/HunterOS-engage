"""
HunterOS Engage V1 - Intent Pipeline Runner
Orchestrates the 6-stage linear deterministic Intent Detection Pipeline.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.recognizer import IntentRecognizer
from app.domain.intents.resolver import IntentResolver
from app.domain.intents.stages.base import IntentPipelineStage
from app.domain.intents.stages.load_stage import LoadArtifactsStage
from app.domain.intents.stages.normalize_stage import NormalizeInputsStage
from app.domain.intents.stages.recognize_stage import RecognizeCandidatesStage
from app.domain.intents.stages.resolve_stage import ResolveDuplicatesStage
from app.domain.intents.stages.result_stage import GenerateResultStage
from app.domain.intents.stages.validation_stage import ValidateEvidenceStage
from app.domain.intents.validation import IntentValidator

logger = logging.getLogger(__name__)


class IntentPipelineRunner:
    """Linear deterministic runner for Intent Detection."""

    def __init__(
        self,
        stages: Optional[List[IntentPipelineStage]] = None,
        recognizer: Optional[IntentRecognizer] = None,
        validator: Optional[IntentValidator] = None,
        resolver: Optional[IntentResolver] = None,
    ):
        self._stages = stages or [
            LoadArtifactsStage(),
            NormalizeInputsStage(validator=validator),
            RecognizeCandidatesStage(recognizer=recognizer),
            ValidateEvidenceStage(validator=validator),
            ResolveDuplicatesStage(resolver=resolver),
            GenerateResultStage(),
        ]

    def execute(self, context: IntentDetectionContext) -> IntentDetectionResult:
        """Executes the pipeline stages in sequence."""
        try:
            for stage in self._stages:
                stage.run(context)

            if not context.result:
                raise RuntimeError("Intent pipeline did not produce an IntentDetectionResult.")

            return context.result
        except Exception as e:
            logger.exception("Error executing Intent Detection Pipeline: %s", e)
            context.add_validation_error(str(e))
            context.transition_to(IntentPipelineState.FAILED)
            raise
