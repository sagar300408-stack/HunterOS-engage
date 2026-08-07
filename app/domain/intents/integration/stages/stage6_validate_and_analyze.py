"""
HunterOS Engage V1 - Stage 6: Validate & Analyze
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.domain.intents.integration.analytics import IntentContextAnalyticsCalculator
from app.domain.intents.integration.context import IntentIntegrationPipelineContext

logger = logging.getLogger(__name__)


class Stage6_ValidateAndAnalyze:
    """Computes completeness score, module presence indicators, and descriptive diagnostics."""

    def __init__(self, analytics_calculator: Optional[IntentContextAnalyticsCalculator] = None) -> None:
        self.analytics_calculator = analytics_calculator or IntentContextAnalyticsCalculator()

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        ctx.completeness_report = self.analytics_calculator.calculate_completeness_report(
            detection_result=ctx.detection_result,
            classification_result=ctx.classification_result,
            evolution_result=ctx.evolution_result,
            resolution_result=ctx.resolution_result,
            conversation_analysis=ctx.conversation_analysis,
            conversation_timeline=ctx.conversation_timeline,
            conversation_insights=ctx.conversation_insights,
        )

        ctx.analytics = self.analytics_calculator.calculate_analytics(
            completeness_report=ctx.completeness_report,
            context_graph=ctx.context_graph,
            assembly_time_ms=0.0,
            validation_errors=ctx.validation_errors,
            warnings=ctx.validation_warnings,
        )

        logger.debug(
            "Stage 6 Analyzed Context: Completeness=%.2f, Modules=%s",
            ctx.completeness_report.completeness_score,
            ctx.completeness_report.missing_modules,
        )
        ctx.stage_timings_ms["stage6_validate_and_analyze_ms"] = (time.perf_counter() - start) * 1000
