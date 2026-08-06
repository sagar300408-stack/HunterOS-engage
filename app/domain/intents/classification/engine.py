"""
HunterOS Engage V1 - Intent Classification Engine
Bounded context orchestrator transforming detected intents into structured business knowledge.
"""

from __future__ import annotations

from typing import List, Optional
import uuid

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.insight.models import ConversationInsightResult
from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.classification.pipeline import (
    IntentClassificationPipeline,
    default_classification_pipeline,
)
from app.domain.intents.models import DetectedIntent, IntentDetectionResult


class IntentClassificationEngine:
    """
    Primary engine for Intent Classification.
    Transforms detected intents into normalized, structured business knowledge.
    Operates with ZERO memory access and zero autonomous actions.
    """

    def __init__(self, pipeline: Optional[IntentClassificationPipeline] = None):
        self._pipeline = pipeline or default_classification_pipeline

    def classify(
        self,
        conversation_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        detected_intents: Optional[List[DetectedIntent]] = None,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        insight_result: Optional[ConversationInsightResult] = None,
        workspace_id: Optional[uuid.UUID] = None,
        customer_id: Optional[str] = None,
        active_plugins: Optional[List[str]] = None,
    ) -> IntentClassificationResult:
        """
        Classifies intents from detection output and upstream conversation artifacts.
        """
        context = IntentClassificationContext(
            conversation_id=conversation_id,
            detection_result=detection_result,
            detected_intents=detected_intents,
            analysis_result=analysis_result,
            timeline=timeline,
            insight_result=insight_result,
            workspace_id=workspace_id,
            customer_id=customer_id,
            active_plugins=active_plugins,
        )
        return self._pipeline.run(context)

    def classify_from_context(
        self,
        context: IntentClassificationContext,
    ) -> IntentClassificationResult:
        """
        Executes classification directly using a pre-constructed context.
        """
        return self._pipeline.run(context)


default_classification_engine = IntentClassificationEngine()
