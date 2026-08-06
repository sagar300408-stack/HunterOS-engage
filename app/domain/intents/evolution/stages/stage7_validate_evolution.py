"""
HunterOS Engage V1 - Evolution Pipeline Stage 7: Validate Evolution
Enforces timeline consistency, legal transitions, and tenant isolation guardrails.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from app.domain.intents.evolution.validation import (
    EvolutionValidator,
    default_evolution_validator,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class ValidateEvolutionStage:
    """
    Stage 7: Validates invariants across generated timelines, event streams, and snapshots.
    """

    def __init__(self, validator: Optional[EvolutionValidator] = None):
        self.validator = validator or default_evolution_validator

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()

        # 1. Validate Timelines
        for timeline in context.projected_timelines.values():
            timeline_errors = self.validator.validate_timeline_consistency(timeline)
            for err in timeline_errors:
                context.add_validation_error(err)

        # 2. Validate Events (no duplicates)
        event_errors = self.validator.validate_events(context.updated_stream.events)
        for err in event_errors:
            context.add_warning(err)

        # 3. Validate Workspace Isolation
        isolation_errors = self.validator.validate_workspace_isolation(
            context.workspace_id, context.updated_stream.events
        )
        for err in isolation_errors:
            context.add_validation_error(err)

        # 4. Validate Confidence Bounds
        for s in context.current_snapshots:
            conf_errors = self.validator.validate_confidence(
                s.confidence, f"Intent {s.intent_id} ({s.taxonomy_path})"
            )
            for err in conf_errors:
                context.add_validation_error(err)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage7_ValidateEvolution", elapsed_ms)
