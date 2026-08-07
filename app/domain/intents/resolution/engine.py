"""
HunterOS Engage V1 - Multi-Intent Resolution Engine
Main entry point orchestrating context creation, pipeline execution, and result aggregation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import MultiIntentResolutionResult
from app.domain.intents.resolution.pipeline import MultiIntentResolutionPipeline
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry
from app.domain.intents.resolution.repository import ResolutionRepository, default_resolution_repository

logger = logging.getLogger(__name__)


class MultiIntentResolutionEngine:
    """
    Multi-Intent Resolution Engine.
    Coordinates artifact ingestion, graph modeling, conflict/dependency analysis,
    group clustering, dominance calculation, and validation guardrails.
    """

    def __init__(
        self,
        pipeline: Optional[MultiIntentResolutionPipeline] = None,
        repository: Optional[ResolutionRepository] = None,
        registry: Optional[IntentResolutionRegistry] = None,
    ) -> None:
        self.registry = registry or default_resolution_registry
        self.pipeline = pipeline or MultiIntentResolutionPipeline(registry=self.registry)
        self.repository = repository or default_resolution_repository

    def resolve(
        self,
        conversation_id: str,
        entity_id: str = "",
        entity_type: str = "CUSTOMER",
        workspace_id: Optional[uuid.UUID] = None,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insight: Optional[Any] = None,
        rule_pack_names: Optional[List[str]] = None,
        plugin_names: Optional[List[str]] = None,
        custom_parameters: Optional[Dict[str, Any]] = None,
        save_result: bool = True,
    ) -> MultiIntentResolutionResult:
        """
        Execute deterministic multi-intent resolution over the provided conversation artifacts.
        """
        context = MultiIntentResolutionContext(
            conversation_id=conversation_id,
            entity_id=entity_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insight=conversation_insight,
            rule_pack_names=rule_pack_names,
            plugin_names=plugin_names,
            custom_parameters=custom_parameters,
        )

        result = self.pipeline.run(context)

        if save_result and self.repository:
            self.repository.save(result)

        return result
