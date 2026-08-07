"""
HunterOS Engage V1 - Intent Integration Pipeline
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Deterministic 7-Stage sequential integration pipeline for Intent Intelligence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.context import IntentIntegrationPipelineContext
from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.stages import (
    Stage1_LoadIntentArtifacts,
    Stage2_ValidateInputs,
    Stage3_ComposeContext,
    Stage4_ApplyProfile,
    Stage5_BuildContextGraph,
    Stage6_ValidateAndAnalyze,
    Stage7_GenerateIntegrationResult,
)
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentIntegrationPipeline:
    """
    Coordinates the 7-stage deterministic Intent Integration Pipeline.
    """

    def __init__(self) -> None:
        self.stage1 = Stage1_LoadIntentArtifacts()
        self.stage2 = Stage2_ValidateInputs()
        self.stage3 = Stage3_ComposeContext()
        self.stage4 = Stage4_ApplyProfile()
        self.stage5 = Stage5_BuildContextGraph()
        self.stage6 = Stage6_ValidateAndAnalyze()
        self.stage7 = Stage7_GenerateIntegrationResult()

    def run(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        profile_type: Union[str, CompositionProfileType] = CompositionProfileType.FULL,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insights: Optional[Any] = None,
        custom_filters: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> IntentIntelligenceContext:
        prof_enum = (
            profile_type if isinstance(profile_type, CompositionProfileType)
            else CompositionProfileType(profile_type) if profile_type in CompositionProfileType.__members__
            else CompositionProfileType.FULL
        )

        ctx = IntentIntegrationPipelineContext(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            profile_type=prof_enum,
            custom_filters=custom_filters,
            options=options or {},
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insights=conversation_insights,
        )

        # Execute 7 Stages Sequentially
        self.stage1.execute(ctx)
        self.stage2.execute(ctx)
        self.stage3.execute(ctx)
        self.stage4.execute(ctx)
        self.stage5.execute(ctx)
        self.stage6.execute(ctx)
        self.stage7.execute(ctx)

        if ctx.assembled_context is None:
            raise RuntimeError(f"Pipeline failed to assemble context for conversation '{conversation_id}'.")

        return ctx.assembled_context
