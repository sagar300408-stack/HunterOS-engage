"""
HunterOS Engage V1 - Evolution Pipeline Stage 8: Generate Evolution Result
Assembles the finalized immutable IntentEvolutionResult aggregate root.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import TYPE_CHECKING
import uuid

from app.domain.intents.evolution.models import (
    EvolutionDiagnostics,
    EvolutionMetadata,
    IntentEvolutionResult,
    IntentLifecycleState,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class GenerateEvolutionResultStage:
    """
    Stage 8: Compiles metrics, diagnostics, and emits the official IntentEvolutionResult.
    """

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()

        now = datetime.now(timezone.utc)

        # Count state distribution across histories
        active_count = 0
        persisting_count = 0
        strengthening_count = 0
        weakening_count = 0
        resolved_count = 0
        closed_count = 0

        for h in context.histories.values():
            st = h.current_state
            if st in (IntentLifecycleState.NEW, IntentLifecycleState.ACTIVE):
                active_count += 1
            elif st == IntentLifecycleState.PERSISTING:
                persisting_count += 1
            elif st == IntentLifecycleState.STRENGTHENING:
                strengthening_count += 1
            elif st == IntentLifecycleState.WEAKENING:
                weakening_count += 1
            elif st == IntentLifecycleState.RESOLVED:
                resolved_count += 1
            elif st == IntentLifecycleState.CLOSED:
                closed_count += 1

        metadata = EvolutionMetadata(
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            total_active_intents=active_count,
            total_persisting_intents=persisting_count,
            total_strengthening_intents=strengthening_count,
            total_weakening_intents=weakening_count,
            total_resolved_intents=resolved_count,
            total_closed_intents=closed_count,
            total_events_generated=len(context.updated_stream.events),
            evaluated_at=now,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage8_GenerateEvolutionResult", elapsed_ms)

        total_exec_time = sum(context.stage_timings.values())

        diagnostics = EvolutionDiagnostics(
            pipeline_execution_time_ms=round(total_exec_time, 3),
            stage_timings_ms=dict(context.stage_timings),
            stages_executed=list(context.stages_executed),
            snapshots_compared=len(context.snapshot_diffs),
            strategies_evaluated=context.strategies_evaluated_count,
            is_valid=len(context.validation_errors) == 0,
            validation_errors=list(context.validation_errors),
            warnings=list(context.warnings),
        )

        result = IntentEvolutionResult(
            evolution_id=uuid.uuid4(),
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            current_conversation_id=context.current_conversation_id,
            intent_histories=list(context.histories.values()),
            timelines=list(context.projected_timelines.values()),
            event_stream=context.updated_stream,
            metadata=metadata,
            diagnostics=diagnostics,
            generated_at=now,
        )

        context.result = result
