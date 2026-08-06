"""
HunterOS Engage V1 - Output Insight Result Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.domain.conversations.insight.context import ConversationInsightContext, InsightPipelineState
from app.domain.conversations.insight.models import (
    ConversationInsightResult,
    InsightDiagnostics,
    InsightMetadata,
    InsightPriority,
)
from app.domain.conversations.insight.stages.base import InsightPipelineStage

logger = logging.getLogger(__name__)


class OutputInsightResultStage(InsightPipelineStage):
    """Synthesizes the immutable ConversationInsightResult aggregate root."""

    @property
    def stage_name(self) -> str:
        return "OutputInsightResultStage"

    def execute(self, context: ConversationInsightContext) -> None:
        context.transition_to(InsightPipelineState.COMPLETED)

        # Ensure Output stage is recorded in stages_executed
        stages = list(context.stages_executed)
        if self.stage_name not in stages:
            stages.append(self.stage_name)

        # Priority breakdown
        crit_c = sum(1 for i in context.all_insights if i.priority == InsightPriority.CRITICAL)
        high_c = sum(1 for i in context.all_insights if i.priority == InsightPriority.HIGH)
        med_c = sum(1 for i in context.all_insights if i.priority == InsightPriority.MEDIUM)
        low_c = sum(1 for i in context.all_insights if i.priority == InsightPriority.LOW)

        # Category distribution
        cat_counts = Counter(i.category.value for i in context.all_insights)

        # Metadata
        metadata = InsightMetadata(
            insight_result_id=uuid.uuid4(),
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            scope_type=context.scope_type,
            total_insights=len(context.all_insights),
            total_risks=len(context.classified_risks),
            total_opportunities=len(context.classified_opportunities),
            total_action_items=len(context.classified_action_items),
            critical_count=crit_c,
            high_count=high_c,
            medium_count=med_c,
            low_count=low_c,
            category_distribution=dict(cat_counts),
            schema_version="1.0.0",
            generator_version="2.2.3",
            generated_at=datetime.now(timezone.utc),
        )

        # Diagnostics
        total_time_ms = sum(context.stage_timings_ms.values())
        diagnostics = InsightDiagnostics(
            pipeline_execution_time_ms=round(total_time_ms, 3),
            stage_timings_ms=dict(context.stage_timings_ms),
            stages_executed=stages,
            warnings=list(context.warnings),
            validation_errors=list(context.validation_errors),
            is_valid=context.is_valid,
        )

        # Aggregate Root
        result = ConversationInsightResult(
            insight_result_id=metadata.insight_result_id,
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            scope_type=context.scope_type,
            metadata=metadata,
            risks=list(context.classified_risks),
            opportunities=list(context.classified_opportunities),
            action_items=list(context.classified_action_items),
            all_insights=list(context.all_insights),
            diagnostics=diagnostics,
            schema_version="1.0.0",
            generator_version="2.2.3",
            created_at=datetime.now(timezone.utc),
        )

        context.result = result
        logger.debug(
            "Synthesized ConversationInsightResult %s for conversation %s (%d insights)",
            result.insight_result_id,
            context.conversation_id,
            len(result.all_insights),
        )
