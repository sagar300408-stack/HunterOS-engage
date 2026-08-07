"""
HunterOS Engage V1 - Intent Context Analytics Calculator
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Pure descriptive diagnostics & analytics across the integrated intent intelligence context.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import sys

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.models import (
    ContextCompletenessReport,
    IntentContextAnalytics,
    IntentContextGraph,
)
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult


class IntentContextAnalyticsCalculator:
    """
    Computes purely descriptive diagnostics and coverage metrics.
    Zero predictive behavior, zero business scoring.
    """

    def calculate_completeness_report(
        self,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insights: Optional[Any] = None,
    ) -> ContextCompletenessReport:
        has_det = bool(detection_result and detection_result.detected_intents)
        has_cls = bool(classification_result and classification_result.classified_intents)
        has_evo = bool(evolution_result and evolution_result.intent_histories)
        has_res = bool(resolution_result and resolution_result.resolved_groups)
        has_ca = conversation_analysis is not None
        has_tl = conversation_timeline is not None
        has_ins = conversation_insights is not None

        core_modules = [has_det, has_cls, has_evo, has_res]
        completeness_score = sum(1.0 for m in core_modules if m) / 4.0

        missing_modules: List[str] = []
        if not has_det:
            missing_modules.append("DETECTION")
        if not has_cls:
            missing_modules.append("CLASSIFICATION")
        if not has_evo:
            missing_modules.append("EVOLUTION")
        if not has_res:
            missing_modules.append("RESOLUTION")

        total_det = len(detection_result.detected_intents) if detection_result else 0
        total_cls = len(classification_result.classified_intents) if classification_result else 0
        total_evo = len(evolution_result.intent_histories) if evolution_result else 0
        total_grp = len(resolution_result.resolved_groups) if resolution_result else 0
        total_cnf = len(resolution_result.resolution_graph.conflicts) if resolution_result and resolution_result.resolution_graph else 0
        total_dep = len(resolution_result.resolution_graph.dependencies) if resolution_result and resolution_result.resolution_graph else 0

        return ContextCompletenessReport(
            has_detection=has_det,
            has_classification=has_cls,
            has_evolution=has_evo,
            has_resolution=has_res,
            has_conversation_analysis=has_ca,
            has_timeline=has_tl,
            has_insights=has_ins,
            completeness_score=round(completeness_score, 2),
            missing_modules=missing_modules,
            total_detected_intents=total_det,
            total_classified_intents=total_cls,
            total_evolution_histories=total_evo,
            total_resolved_groups=total_grp,
            total_conflicts=total_cnf,
            total_dependencies=total_dep,
        )

    def calculate_analytics(
        self,
        completeness_report: ContextCompletenessReport,
        context_graph: IntentContextGraph,
        assembly_time_ms: float = 0.0,
        validation_errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> IntentContextAnalytics:
        # Module coverage
        module_coverage = completeness_report.completeness_score

        # Intent coverage (ratio of resolved vs detected)
        if completeness_report.total_detected_intents > 0:
            intent_coverage = min(1.0, completeness_report.total_resolved_groups / completeness_report.total_detected_intents)
        else:
            intent_coverage = 1.0 if completeness_report.total_resolved_groups > 0 else 0.0

        # Estimated size
        composition_size_bytes = len(context_graph.nodes) * 256 + len(context_graph.links) * 128

        # Dominant intents
        dominant_count = sum(
            1 for n in context_graph.nodes.values()
            if n.attributes.get("is_dominant") or n.subsystem == "RESOLUTION_GROUP"
        )

        validation_summary = {
            "is_valid": len(validation_errors or []) == 0,
            "error_count": len(validation_errors or []),
            "warning_count": len(warnings or []),
            "errors": validation_errors or [],
            "warnings": warnings or [],
        }

        return IntentContextAnalytics(
            intent_coverage=round(intent_coverage, 2),
            module_coverage=round(module_coverage, 2),
            missing_modules=completeness_report.missing_modules,
            composition_size_bytes=composition_size_bytes,
            total_intent_count=len(context_graph.nodes),
            resolved_group_count=completeness_report.total_resolved_groups,
            unresolved_conflict_count=completeness_report.total_conflicts,
            dominant_intents_count=dominant_count,
            assembly_time_ms=round(assembly_time_ms, 2),
            validation_summary=validation_summary,
        )
