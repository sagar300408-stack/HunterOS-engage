"""
HunterOS Engage V1 - Normalize Inputs Stage
Harmonizes conversation identifiers and asserts cross-workspace isolation.
"""

from __future__ import annotations

import uuid

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.stages.base import IntentPipelineStage
from app.domain.intents.validation import IntentValidator, default_intent_validator


class NormalizeInputsStage(IntentPipelineStage):
    """Aligns conversation_id, workspace_id, customer_id and validates cross-workspace isolation."""

    def __init__(self, validator: IntentValidator = None):
        self._validator = validator or default_intent_validator

    @property
    def stage_name(self) -> str:
        return "NormalizeInputsStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.NORMALIZING

    def execute(self, context: IntentDetectionContext) -> None:
        # Align conversation_id
        if not context.conversation_id:
            if context.analysis_result and hasattr(context.analysis_result, "conversation_id"):
                context.conversation_id = str(context.analysis_result.conversation_id)
            elif context.timeline and hasattr(context.timeline, "conversation_id"):
                context.conversation_id = str(context.timeline.conversation_id)
            elif context.insight_result and hasattr(context.insight_result, "conversation_id"):
                context.conversation_id = str(context.insight_result.conversation_id)

        # Align workspace_id
        if not context.workspace_id:
            if context.analysis_result and hasattr(context.analysis_result, "workspace_id"):
                ws = context.analysis_result.workspace_id
                context.workspace_id = uuid.UUID(str(ws)) if ws else None
            elif context.timeline and hasattr(context.timeline, "workspace_id"):
                ws = context.timeline.workspace_id
                context.workspace_id = uuid.UUID(str(ws)) if ws else None
            elif context.insight_result and hasattr(context.insight_result, "workspace_id"):
                ws = context.insight_result.workspace_id
                context.workspace_id = uuid.UUID(str(ws)) if ws else None

        # Align customer_id safely
        if not context.customer_id:
            for art in (context.analysis_result, context.timeline, context.insight_result):
                cid = getattr(art, "customer_id", None)
                if cid:
                    context.customer_id = str(cid)
                    break

        # Validate cross-workspace isolation invariants
        invariant_errors = self._validator.validate_context_invariants(context)
        for err in invariant_errors:
            context.add_validation_error(err)
