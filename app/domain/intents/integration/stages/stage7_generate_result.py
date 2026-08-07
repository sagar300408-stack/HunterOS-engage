"""
HunterOS Engage V1 - Stage 7: Generate Integration Result
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import List
import uuid

from app.domain.intents.integration.context import IntentIntegrationPipelineContext
from app.domain.intents.integration.models import (
    ContextDiagnostics,
    ContextMetadata,
    ContextProvenance,
    IntentIntelligenceContext,
)

logger = logging.getLogger(__name__)


class Stage7_GenerateIntegrationResult:
    """Packages final IntentIntelligenceContext aggregate with full provenance and CQRS views."""

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        cid = uuid.uuid4()
        now_dt = datetime.now(timezone.utc)
        profile = ctx.active_profile
        profile_key = profile.profile_type.value if profile and hasattr(profile.profile_type, "value") else (str(profile.profile_type) if profile else "FULL")

        source_modules: List[str] = []
        if ctx.detection_result and (not profile or profile.include_detection):
            source_modules.append("DETECTION")
        if ctx.classification_result and (not profile or profile.include_classification):
            source_modules.append("CLASSIFICATION")
        if ctx.evolution_result and (not profile or profile.include_evolution):
            source_modules.append("EVOLUTION")
        if ctx.resolution_result and (not profile or profile.include_resolution):
            source_modules.append("RESOLUTION")
        if ctx.conversation_analysis and (not profile or profile.include_conversation_context):
            source_modules.append("CONVERSATION_ANALYSIS")

        metadata = ContextMetadata(
            context_id=cid,
            conversation_id=ctx.conversation_id,
            entity_id=ctx.entity_id,
            workspace_id=ctx.workspace_id,
            composition_profile=profile_key,
            source_modules=source_modules,
            created_at=now_dt,
        )

        provenance = ContextProvenance(
            integration_version="1.0.0",
            gateway_version="1.0.0",
            pipeline_version="1.0.0",
            engine_version="1.0.0",
            composition_profile=profile_key,
            source_modules=source_modules,
            detection_provenance=ctx.detection_result.provenance.model_dump() if ctx.detection_result and hasattr(ctx.detection_result, "provenance") and hasattr(ctx.detection_result.provenance, "model_dump") else None,
            classification_provenance=ctx.classification_result.provenance.model_dump() if ctx.classification_result and hasattr(ctx.classification_result, "provenance") and hasattr(ctx.classification_result.provenance, "model_dump") else None,
            evolution_provenance=ctx.evolution_result.provenance.model_dump() if ctx.evolution_result and hasattr(ctx.evolution_result, "provenance") and hasattr(ctx.evolution_result.provenance, "model_dump") else None,
            resolution_provenance=ctx.resolution_result.provenance.model_dump() if ctx.resolution_result and hasattr(ctx.resolution_result, "provenance") and hasattr(ctx.resolution_result.provenance, "model_dump") else None,
            generated_at=now_dt,
        )

        total_timings = dict(ctx.stage_timings_ms)
        total_duration = sum(total_timings.values())

        diagnostics = ContextDiagnostics(
            is_valid=ctx.is_valid,
            warnings=ctx.validation_warnings,
            validation_errors=ctx.validation_errors,
            evaluation_timings_ms=total_timings,
            total_duration_ms=round(total_duration, 2),
            artifacts_processed=len(source_modules),
            rules_applied=ctx.rules_applied,
        )

        # Update analytics assembly time
        if ctx.analytics:
            ctx.analytics.assembly_time_ms = round(total_duration, 2)

        root_context = IntentIntelligenceContext(
            context_id=cid,
            conversation_id=ctx.conversation_id,
            entity_id=ctx.entity_id,
            workspace_id=ctx.workspace_id,
            detection_result=ctx.detection_result if (not profile or profile.include_detection) else None,
            classification_result=ctx.classification_result if (not profile or profile.include_classification) else None,
            evolution_result=ctx.evolution_result if (not profile or profile.include_evolution) else None,
            resolution_result=ctx.resolution_result if (not profile or profile.include_resolution) else None,
            conversation_analysis=ctx.conversation_analysis if (not profile or profile.include_conversation_context) else None,
            conversation_timeline=ctx.conversation_timeline if (not profile or profile.include_conversation_context) else None,
            conversation_insights=ctx.conversation_insights if (not profile or profile.include_conversation_context) else None,
            context_graph=ctx.context_graph,
            analytics=ctx.analytics,
            completeness_report=ctx.completeness_report,
            metadata=metadata,
            provenance=provenance,
            diagnostics=diagnostics,
        )

        # Apply profile projections
        if profile:
            profile.apply(root_context, ctx.options or ctx.custom_filters or {})

        ctx.assembled_context = root_context
        ctx.stage_timings_ms["stage7_generate_result_ms"] = (time.perf_counter() - start) * 1000
