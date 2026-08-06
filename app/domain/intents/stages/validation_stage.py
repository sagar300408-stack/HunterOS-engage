"""
HunterOS Engage V1 - Validate Evidence Stage
Validates evidence completeness and invariant boundary rules for all candidate intents.
"""

from __future__ import annotations

from typing import Optional

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.stages.base import IntentPipelineStage
from app.domain.intents.validation import IntentValidator, default_intent_validator


class ValidateEvidenceStage(IntentPipelineStage):
    """Filters candidate intents through the IntentValidator."""

    def __init__(self, validator: Optional[IntentValidator] = None):
        self._validator = validator or default_intent_validator

    @property
    def stage_name(self) -> str:
        return "ValidateEvidenceStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.VALIDATING

    def execute(self, context: IntentDetectionContext) -> None:
        validated = []
        for candidate in context.candidate_intents:
            errors = self._validator.validate_candidate(candidate, context)
            if errors:
                for err in errors:
                    context.add_validation_error(err)
            else:
                validated.append(candidate)

        context.validated_intents = validated
