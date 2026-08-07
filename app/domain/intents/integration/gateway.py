"""
HunterOS Engage V1 - Intent Intelligence Gateway
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Anti-Corruption Layer (ACL) and public entry point orchestrating all Intent Intelligence operations.
Downstream domains (Customer Journey, Recommendations, Executive, Analytics) must interact
exclusively through this gateway.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.intents.api import intent_api_v1
from app.domain.intents.classification.api import intent_classification_api_v1
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.api import intent_evolution_api_v1
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.assembler import IntentContextAssembler
from app.domain.intents.integration.cache import IIntentContextCache, NullIntentContextCache
from app.domain.intents.integration.engines.composition import IntentCompositionEngine
from app.domain.intents.integration.engines.export import IntentExportEngine
from app.domain.intents.integration.engines.query import IntentQueryEngine
from app.domain.intents.integration.models import (
    CompositionProfileType,
    ContextGraphNode,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.pipeline import IntentIntegrationPipeline
from app.domain.intents.integration.registry import IntentContextRegistry, default_context_registry
from app.domain.intents.integration.repository import IntentContextRepository, default_context_repository
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.api_v1 import IntentResolutionAPIv1
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentIntelligenceGateway:
    """
    Unified public entry point and Anti-Corruption Layer.
    Orchestrates Detection, Classification, Evolution, Resolution, Integration, and Queries.
    """

    def __init__(
        self,
        pipeline: Optional[IntentIntegrationPipeline] = None,
        assembler: Optional[IntentContextAssembler] = None,
        query_engine: Optional[IntentQueryEngine] = None,
        export_engine: Optional[IntentExportEngine] = None,
        composition_engine: Optional[IntentCompositionEngine] = None,
        repository: Optional[IntentContextRepository] = None,
        cache: Optional[IIntentContextCache] = None,
        registry: Optional[IntentContextRegistry] = None,
    ) -> None:
        self.repository = repository or default_context_repository
        self.cache = cache or NullIntentContextCache()
        self.registry = registry or default_context_registry
        self.assembler = assembler or IntentContextAssembler()
        self.query_engine = query_engine or IntentQueryEngine(repository=self.repository, cache=self.cache)
        self.export_engine = export_engine or IntentExportEngine()
        self.composition_engine = composition_engine or IntentCompositionEngine(assembler=self.assembler, registry=self.registry)
        self.pipeline = pipeline or IntentIntegrationPipeline()

        # Direct Subsystem API references
        self._detection_api = intent_api_v1
        self._classification_api = intent_classification_api_v1
        self._evolution_api = intent_evolution_api_v1
        self._resolution_api = IntentResolutionAPIv1()

    # ── Pipeline Orchestration ────────────────────────────────────────────────

    def integrate(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        profile: Union[str, CompositionProfileType] = CompositionProfileType.FULL,
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
        """Run the 7-stage deterministic integration pipeline and persist context."""
        context = self.pipeline.run(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            profile_type=profile,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insights=conversation_insights,
            custom_filters=custom_filters,
            options=options,
        )

        # Save to repository
        self.repository.save(context)
        return context

    # ── Subsystem Delegations ─────────────────────────────────────────────────

    def detect_intents(self, conversation_id: str, messages: List[Dict[str, Any]], entity_id: str, workspace_id: str) -> Optional[IntentDetectionResult]:
        """Detect raw intents via Detection Subsystem (Phase 2.3.1)."""
        return self._detection_api.detect_intents(
            conversation_id=conversation_id,
            messages=messages,
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

    def classify_intents(self, conversation_id: str, entity_id: str, workspace_id: str, detection_result: Optional[IntentDetectionResult] = None) -> Optional[IntentClassificationResult]:
        """Classify intents via Classification Subsystem (Phase 2.3.2)."""
        if detection_result:
            return self._classification_api.classify_detection_result(detection_result)
        return self._classification_api.get_classification(conversation_id)

    def evolve_intents(self, conversation_id: str, entity_id: str, workspace_id: str, classification_result: Optional[IntentClassificationResult] = None) -> Optional[IntentEvolutionResult]:
        """Evolve intents via Evolution Subsystem (Phase 2.3.3)."""
        if classification_result:
            return self._evolution_api.process_classification_result(classification_result)
        return self._evolution_api.get_evolution_result(conversation_id)

    def resolve_intents(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
    ) -> Optional[MultiIntentResolutionResult]:
        """Resolve multi-intent graph via Resolution Subsystem (Phase 2.3.4)."""
        from app.domain.intents.resolution.schemas import ResolveIntentsRequest
        req = ResolveIntentsRequest(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
        )
        resp = self._resolution_api.resolve_intents(
            request=req,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
        )
        return self._resolution_api.repository.get_by_conversation(conversation_id)

    # ── Queries & Graph Navigation ────────────────────────────────────────────

    def get_context(self, conversation_id: str, profile: Optional[Union[str, CompositionProfileType]] = None) -> Optional[IntentIntelligenceContext]:
        return self.query_engine.get_by_conversation(conversation_id, profile=profile)

    def get_context_by_id(self, context_id: uuid.UUID) -> Optional[IntentIntelligenceContext]:
        return self.query_engine.get_by_id(context_id)

    def query_contexts(
        self,
        workspace_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        profile: Optional[Union[str, CompositionProfileType]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IntentIntelligenceContext]:
        return self.query_engine.query(
            workspace_id=workspace_id,
            entity_id=entity_id,
            conversation_id=conversation_id,
            profile=profile,
            limit=limit,
            offset=offset,
        )

    def get_intent_lineage(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        return self.query_engine.get_intent_lineage(conversation_id, intent_id)

    def get_intent_conflicts(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        return self.query_engine.get_intent_conflicts(conversation_id, intent_id)

    def get_intent_dependencies(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        return self.query_engine.get_intent_dependencies(conversation_id, intent_id)


# Global default gateway instance
default_intent_gateway = IntentIntelligenceGateway()
