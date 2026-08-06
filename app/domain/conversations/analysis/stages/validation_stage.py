"""
HunterOS Engage — Validation Stage (Phase 2.2.1)

Validates analysis artifacts and checks provenance, bounds, and boundary invariants.
"""

from __future__ import annotations

from typing import Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage
from app.domain.conversations.analysis.validation import (
    AnalysisValidationFramework,
)


class ValidationStage(PipelineStage):
    """Pipeline stage executing comprehensive analysis validation."""

    def __init__(self, validator: Optional[AnalysisValidationFramework] = None) -> None:
        self._validator = validator or AnalysisValidationFramework()

    @property
    def stage_name(self) -> str:
        return "ValidationStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.VALIDATING

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        return self._validator.validate(context)
