"""
HunterOS Engage V1 - Stage 9: Generate Resolution Result
Assembles metadata, diagnostics, provenance, and emits the immutable MultiIntentResolutionResult aggregate root.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    GraphSnapshot,
    MultiIntentResolutionResult,
    ResolutionDiagnostics,
    ResolutionMetadata,
    ResolutionProvenance,
)


class Stage9_GenerateResolutionResult:
    """
    Stage 9: Final assembly and freeze of the MultiIntentResolutionResult artifact.
    """

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()

        now = datetime.now(timezone.utc)
        total_time_ms = context.elapsed_ms()

        # Build GraphSnapshot
        snapshot = context.resolution_graph.create_snapshot(
            graph_version="1.0.0",
            group_count=len(context.resolved_groups),
            dominant_count=len(context.dominant_intents),
        ) if context.resolution_graph else GraphSnapshot()

        # Build Metadata
        metadata = ResolutionMetadata(
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            conversation_id=context.conversation_id,
            total_input_intents=len(context.normalized_nodes),
            total_groups=len(context.resolved_groups),
            total_relationships=len(context.analyzed_relationships),
            total_conflicts=len(context.analyzed_conflicts),
            total_dependencies=len(context.analyzed_dependencies),
            total_dominant_intents=len(context.dominant_intents),
            evaluated_at=now,
        )

        # Build Diagnostics
        is_valid = len(context.validation_errors) == 0
        diagnostics = ResolutionDiagnostics(
            pipeline_execution_time_ms=round(total_time_ms, 3),
            stage_timings_ms={k: round(v, 3) for k, v in context.stage_timings_ms.items()},
            stages_executed=list(context.stages_executed) + ["Stage9_GenerateResolutionResult"],
            rules_evaluated=context.rules_evaluated_count,
            strategies_evaluated=context.strategies_evaluated_count,
            is_valid=is_valid,
            validation_errors=list(context.validation_errors),
            warnings=list(context.warnings),
        )

        # Build Provenance
        provenance = ResolutionProvenance(
            resolution_version="1.0.0",
            graph_version="1.0.0",
            rule_pack_version="1.0.0",
            pipeline_version="2.3.4",
            engine_version="1.0.0",
            rule_packs_applied=list(context.rule_packs_applied),
            plugins_applied=list(context.plugin_names or ["CrossIndustryResolutionPlugin"]),
            generated_at=now,
        )

        # Assemble Aggregate Root
        context.result = MultiIntentResolutionResult(
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            conversation_id=context.conversation_id,
            resolution_graph=context.resolution_graph,
            groups=context.resolved_groups,
            dominant_intents=context.dominant_intents,
            snapshot=snapshot,
            metadata=metadata,
            diagnostics=diagnostics,
            provenance=provenance,
            generated_at=now,
        )

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage9_GenerateResolutionResult", duration)
