"""
HunterOS Engage V1 - Generate Result Stage
Assembles final immutable IntentDetectionResult aggregate with telemetry and metadata.
"""

from __future__ import annotations

import time
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.models import (
    IntentDetectionResult,
    IntentDiagnostics,
    IntentMetadata,
    IntentTaxonomyCategory,
)
from app.domain.intents.stages.base import IntentPipelineStage


class GenerateResultStage(IntentPipelineStage):
    """Compiles the final IntentDetectionResult aggregate root."""

    @property
    def stage_name(self) -> str:
        return "GenerateResultStage"

    @property
    def target_state(self) -> IntentPipelineState:
        return IntentPipelineState.RESULT_GENERATION

    def execute(self, context: IntentDetectionContext) -> None:
        total_time_ms = round((time.perf_counter() - context.start_time) * 1000.0, 3)
        intents = list(context.resolved_intents)

        # Compute metadata distributions
        cat_counts = Counter([i.taxonomy_category.value for i in intents])
        type_counts = Counter([i.intent_type.value for i in intents])
        avg_conf = (
            round(sum(i.confidence for i in intents) / len(intents), 3)
            if intents
            else 0.0
        )
        primary_intent = intents[0].intent_type if intents else None

        dominant_cat = None
        if cat_counts:
            most_common_cat_val = cat_counts.most_common(1)[0][0]
            dominant_cat = IntentTaxonomyCategory(most_common_cat_val)

        metadata = IntentMetadata(
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            total_intents=len(intents),
            primary_intent=primary_intent,
            dominant_category=dominant_cat,
            category_distribution=dict(cat_counts),
            type_distribution=dict(type_counts),
            average_confidence=avg_conf,
            generated_at=datetime.now(timezone.utc),
        )

        diagnostics = IntentDiagnostics(
            pipeline_execution_time_ms=total_time_ms,
            stage_timings_ms=dict(context.stage_timings_ms),
            stages_executed=list(context.stages_executed),
            rules_evaluated=len(context.rule_execution_report.executed_rules),
            intents_detected_raw=len(context.candidate_intents),
            intents_deduplicated=len(context.candidate_intents) - len(intents),
            rule_report=context.rule_execution_report,
            warnings=list(context.warnings),
            validation_errors=list(context.validation_errors),
            is_valid=context.is_valid,
        )

        detection_id = uuid.uuid4()
        result = IntentDetectionResult(
            detection_id=detection_id,
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            detected_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
            intents=intents,
            metadata=metadata,
            diagnostics=diagnostics,
        )

        context.result = result
        context.transition_to(IntentPipelineState.COMPLETED)
