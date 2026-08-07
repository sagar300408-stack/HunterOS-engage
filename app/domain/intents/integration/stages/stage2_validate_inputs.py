"""
HunterOS Engage V1 - Stage 2: Validate Inputs
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

import logging
import time

from app.domain.intents.integration.context import IntentIntegrationPipelineContext
from app.domain.intents.integration.validation import IntentContextValidator

logger = logging.getLogger(__name__)


class Stage2_ValidateInputs:
    """Zero-trust validation of workspace isolation, conversation IDs, and referential integrity."""

    def __init__(self, validator: Optional[IntentContextValidator] = None) -> None:
        self.validator = validator or IntentContextValidator()

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        errors = self.validator.validate_inputs(
            conversation_id=ctx.conversation_id,
            entity_id=ctx.entity_id,
            workspace_id=ctx.workspace_id,
            detection_result=ctx.detection_result,
            classification_result=ctx.classification_result,
            evolution_result=ctx.evolution_result,
            resolution_result=ctx.resolution_result,
        )
        warnings = self.validator.validate_cross_subsystem_references(
            detection_result=ctx.detection_result,
            classification_result=ctx.classification_result,
            evolution_result=ctx.evolution_result,
            resolution_result=ctx.resolution_result,
        )

        ctx.validation_errors.extend(errors)
        ctx.validation_warnings.extend(warnings)
        if errors:
            ctx.is_valid = False
            logger.warning("Stage 2 Validation failed with %d errors for conversation %s", len(errors), ctx.conversation_id)

        ctx.stage_timings_ms["stage2_validate_inputs_ms"] = (time.perf_counter() - start) * 1000
