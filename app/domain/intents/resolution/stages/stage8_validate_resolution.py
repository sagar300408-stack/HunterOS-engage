"""
HunterOS Engage V1 - Stage 8: Validate Resolution
Runs zero-trust validation guardrails over graph topology, conflicts, dependencies, and tenant isolation.
"""

from __future__ import annotations

import time

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.validation import MultiIntentResolutionValidator


class Stage8_ValidateResolution:
    """
    Stage 8: Executes comprehensive validation guardrails on the resolved graph model.
    """

    def __init__(self, validator: MultiIntentResolutionValidator | None = None) -> None:
        self.validator = validator or MultiIntentResolutionValidator()

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()

        is_valid = self.validator.validate(context)

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage8_ValidateResolution", duration)
