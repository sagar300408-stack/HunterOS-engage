"""
HunterOS Engage V1 - Intent Context Assembler
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Assembles multiple bounded context artifacts (Detection, Classification, Evolution, Resolution)
into a unified IntentIntelligenceContext aggregate.
Zero reasoning, zero prediction, zero inference of missing data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.analytics import IntentContextAnalyticsCalculator
from app.domain.intents.integration.graph import IntentContextGraphBuilder
from app.domain.intents.integration.models import (
    CompositionProfileType,
    ContextDiagnostics,
    ContextMetadata,
    ContextProvenance,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.profiles.base import CompositionProfile
from app.domain.intents.integration.registry import default_context_registry
from app.domain.intents.integration.validation import IntentContextValidator
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentContextAssembler:
    """
    Multi-bounded context assembler.
    Combines artifacts from Detection, Classification, Evolution, and Resolution
    into an immutable IntentIntelligenceContext.
    """

    def __init__(
        self,
        validator: Optional[IntentContextValidator] = None,
        graph_builder: Optional[IntentContextGraphBuilder] = None,
        analytics_calculator: Optional[IntentContextAnalyticsCalculator] = None,
    ) -> None:
        self.validator = validator or IntentContextValidator()
        self.graph_builder = graph_builder or IntentContextGraphBuilder()
        self.analytics_calculator = analytics_calculator or IntentContextAnalyticsCalculator()

    def assemble(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insights: Optional[Any] = None,
        profile: Optional[CompositionProfile] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> IntentIntelligenceContext:
        start_time = time.perf_counter()
        timings: Dict[str, float] = {}

        active_profile = profile or default_context_registry.get_profile(CompositionProfileType.FULL)
        profile_key = active_profile.profile_type.value if hasattr(active_profile.profile_type, "value") else str(active_profile.profile_type)

        # 1. Zero-trust Validation
        val_start = time.perf_counter()
        val_errors = self.validator.validate_inputs(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
        )
        val_warnings = self.validator.validate_cross_subsystem_references(
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
        )
        timings["validation_ms"] = (time.perf_counter() - val_start) * 1000

        # 2. Build Relational Graph
        graph_start = time.perf_counter()
        context_graph = self.graph_builder.build_graph(
            detection_result=detection_result if active_profile.include_detection else None,
            classification_result=classification_result if active_profile.include_classification else None,
            evolution_result=evolution_result if active_profile.include_evolution else None,
            resolution_result=resolution_result if active_profile.include_resolution else None,
        )
        timings["graph_building_ms"] = (time.perf_counter() - graph_start) * 1000

        # 3. Completeness & Analytics
        analytics_start = time.perf_counter()
        completeness_report = self.analytics_calculator.calculate_completeness_report(
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insights=conversation_insights,
        )
        analytics = self.analytics_calculator.calculate_analytics(
            completeness_report=completeness_report,
            context_graph=context_graph,
            assembly_time_ms=(time.perf_counter() - start_time) * 1000,
            validation_errors=val_errors,
            warnings=val_warnings,
        )
        timings["analytics_ms"] = (time.perf_counter() - analytics_start) * 1000

        # 4. Track Active Source Modules
        source_modules: List[str] = []
        if detection_result and active_profile.include_detection:
            source_modules.append("DETECTION")
        if classification_result and active_profile.include_classification:
            source_modules.append("CLASSIFICATION")
        if evolution_result and active_profile.include_evolution:
            source_modules.append("EVOLUTION")
        if resolution_result and active_profile.include_resolution:
            source_modules.append("RESOLUTION")
        if conversation_analysis and active_profile.include_conversation_context:
            source_modules.append("CONVERSATION_ANALYSIS")

        # 5. Build Metadata & Provenance
        cid = uuid.uuid4()
        now_dt = datetime.now(timezone.utc)
        metadata = ContextMetadata(
            context_id=cid,
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
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
            detection_provenance=detection_result.provenance.model_dump() if detection_result and hasattr(detection_result, "provenance") and hasattr(detection_result.provenance, "model_dump") else None,
            classification_provenance=classification_result.provenance.model_dump() if classification_result and hasattr(classification_result, "provenance") and hasattr(classification_result.provenance, "model_dump") else None,
            evolution_provenance=evolution_result.provenance.model_dump() if evolution_result and hasattr(evolution_result, "provenance") and hasattr(evolution_result.provenance, "model_dump") else None,
            resolution_provenance=resolution_result.provenance.model_dump() if resolution_result and hasattr(resolution_result, "provenance") and hasattr(resolution_result.provenance, "model_dump") else None,
            generated_at=now_dt,
        )

        total_duration = (time.perf_counter() - start_time) * 1000
        diagnostics = ContextDiagnostics(
            is_valid=len(val_errors) == 0,
            warnings=val_warnings,
            validation_errors=val_errors,
            evaluation_timings_ms=timings,
            total_duration_ms=round(total_duration, 2),
            artifacts_processed=len(source_modules),
            rules_applied=[],
        )

        # 6. Instantiate Root Context
        context = IntentIntelligenceContext(
            context_id=cid,
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            detection_result=detection_result if active_profile.include_detection else None,
            classification_result=classification_result if active_profile.include_classification else None,
            evolution_result=evolution_result if active_profile.include_evolution else None,
            resolution_result=resolution_result if active_profile.include_resolution else None,
            conversation_analysis=conversation_analysis if active_profile.include_conversation_context else None,
            conversation_timeline=conversation_timeline if active_profile.include_conversation_context else None,
            conversation_insights=conversation_insights if active_profile.include_conversation_context else None,
            context_graph=context_graph,
            analytics=analytics,
            completeness_report=completeness_report,
            metadata=metadata,
            provenance=provenance,
            diagnostics=diagnostics,
        )

        # 7. Apply Profile Transformations
        prof_start = time.perf_counter()
        active_profile.apply(context, options or {})
        timings["profile_application_ms"] = (time.perf_counter() - prof_start) * 1000
        context.diagnostics.evaluation_timings_ms = timings

        return context
