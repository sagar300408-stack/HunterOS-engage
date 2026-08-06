"""
HunterOS Engage V1 - Conversation Insight Engine Facade
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Central orchestrator coordinating the 8-stage insight processing pipeline,
detector registries, validation, classification, and view projection generation.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.insight.classification import (
    InsightClassifier,
    default_insight_classifier,
)
from app.domain.conversations.insight.context import (
    ConversationInsightContext,
    InsightPipelineState,
)
from app.domain.conversations.insight.detectors.actions.registry import (
    ActionItemDetectorRegistry,
    default_action_item_detector_registry,
)
from app.domain.conversations.insight.detectors.opportunities.registry import (
    OpportunityDetectorRegistry,
    default_opportunity_detector_registry,
)
from app.domain.conversations.insight.detectors.risks.registry import (
    RiskDetectorRegistry,
    default_risk_detector_registry,
)
from app.domain.conversations.insight.models import (
    ConversationInsightResult,
    InsightScopeType,
)
from app.domain.conversations.insight.repository import (
    InMemoryInsightRepository,
    default_insight_repository,
)
from app.domain.conversations.insight.stages.action_stage import DetectActionItemsStage
from app.domain.conversations.insight.stages.base import InsightPipelineStage
from app.domain.conversations.insight.stages.classify_stage import ClassifyInsightsStage
from app.domain.conversations.insight.stages.load_stage import LoadArtifactsStage
from app.domain.conversations.insight.stages.normalize_stage import NormalizeInputsStage
from app.domain.conversations.insight.stages.opportunity_stage import DetectOpportunitiesStage
from app.domain.conversations.insight.stages.output_stage import OutputInsightResultStage
from app.domain.conversations.insight.stages.risk_stage import DetectRisksStage
from app.domain.conversations.insight.stages.validate_stage import ValidateInsightsStage
from app.domain.conversations.insight.validation import (
    InsightValidationFramework,
    default_insight_validation_framework,
)
from app.domain.conversations.insight.views.registry import (
    InsightViewRegistry,
    default_insight_view_registry,
)
from app.domain.conversations.timeline.models import ConversationTimeline

logger = logging.getLogger(__name__)


class ConversationInsightEngine:
    """
    Main entry point for generating structured descriptive business insights
    (Risks, Opportunities, Action Items) from conversation artifacts.
    """

    def __init__(
        self,
        risk_registry: Optional[RiskDetectorRegistry] = None,
        opportunity_registry: Optional[OpportunityDetectorRegistry] = None,
        action_registry: Optional[ActionItemDetectorRegistry] = None,
        view_registry: Optional[InsightViewRegistry] = None,
        classifier: Optional[InsightClassifier] = None,
        validator: Optional[InsightValidationFramework] = None,
        repository: Optional[InMemoryInsightRepository] = None,
    ) -> None:
        self.risk_registry = risk_registry or default_risk_detector_registry
        self.opportunity_registry = opportunity_registry or default_opportunity_detector_registry
        self.action_registry = action_registry or default_action_item_detector_registry
        self.view_registry = view_registry or default_insight_view_registry
        self.classifier = classifier or default_insight_classifier
        self.validator = validator or default_insight_validation_framework
        self.repository = repository or default_insight_repository

        self._stages: List[InsightPipelineStage] = [
            LoadArtifactsStage(),
            NormalizeInputsStage(),
            DetectRisksStage(self.risk_registry),
            DetectOpportunitiesStage(self.opportunity_registry),
            DetectActionItemsStage(self.action_registry),
            ClassifyInsightsStage(self.classifier),
            ValidateInsightsStage(self.validator),
            OutputInsightResultStage(),
        ]

    def build_insights(
        self,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        scope_type: InsightScopeType = InsightScopeType.CONVERSATION,
        **kwargs: Any,
    ) -> ConversationInsightResult:
        """
        Executes the 8-stage deterministic insight pipeline on input artifacts.
        """
        context = ConversationInsightContext(
            analysis_result=analysis_result,
            timeline=timeline,
            customer_id=kwargs.get("customer_id"),
            scope_type=scope_type,
        )

        for stage in self._stages:
            t0 = time.perf_counter()
            try:
                stage.execute(context)
            except Exception as e:
                logger.error("Stage %s failed: %s", stage.stage_name, str(e), exc_info=True)
                context.add_validation_error(f"Stage {stage.stage_name} failed: {str(e)}")
                context.transition_to(InsightPipelineState.FAILED)
                raise
            finally:
                t1 = time.perf_counter()
                elapsed_ms = (t1 - t0) * 1000.0
                context.record_stage_execution(stage.stage_name, elapsed_ms)

        if not context.result:
            raise RuntimeError("Pipeline failed to synthesize ConversationInsightResult output.")

        # Persist result
        if self.repository:
            self.repository.save(context.result)

        return context.result

    def render_view(
        self,
        result: ConversationInsightResult,
        view_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Renders an insight projection view (e.g. 'executive', 'sales', 'operations', 'audit')."""
        return self.view_registry.render_view(view_name, result, **kwargs)

    def validate_result(self, result: ConversationInsightResult) -> List[str]:
        """Validates an insight aggregate directly."""
        return self.validator.validate_result(result)


default_conversation_insight_engine = ConversationInsightEngine()
