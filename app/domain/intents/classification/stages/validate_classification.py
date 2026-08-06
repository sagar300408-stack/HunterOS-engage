"""
HunterOS Engage V1 - Classification Stage 7: Validate Classification
"""

from __future__ import annotations

import time
from typing import Optional

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.validation import (
    IntentClassificationValidator,
    default_classification_validator,
)


class ValidateClassificationStage:
    """Stage 7: Validates graph references, relationships, isolation, and architectural bounds."""

    def __init__(self, validator: Optional[IntentClassificationValidator] = None):
        self._validator = validator or default_classification_validator

    def execute(self, context: IntentClassificationContext) -> bool:
        start = time.perf_counter()
        is_valid = self._validator.validate(context)
        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage7_ValidateClassification", elapsed)
        return is_valid
