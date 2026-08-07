"""
HunterOS Engage V1 - Intent Intelligence Platform
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Root Platform orchestrator encapsulating Gateway, Context Assembler, Query Engine,
Export Engine, Composition Engine, and Registry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.assembler import IntentContextAssembler
from app.domain.intents.integration.cache import IIntentContextCache, NullIntentContextCache
from app.domain.intents.integration.engines.composition import IntentCompositionEngine
from app.domain.intents.integration.engines.export import IntentExportEngine
from app.domain.intents.integration.engines.query import IntentQueryEngine
from app.domain.intents.integration.gateway import IntentIntelligenceGateway
from app.domain.intents.integration.models import (
    AuditIntentContext,
    CompositionProfileType,
    CustomIntentContext,
    ExecutiveIntentContext,
    IntentIntelligenceContext,
    OperationsIntentContext,
    SalesIntentContext,
)
from app.domain.intents.integration.pipeline import IntentIntegrationPipeline
from app.domain.intents.integration.registry import (
    IntentContextRegistry,
    IntentIntelligencePlugin,
    default_context_registry,
)
from app.domain.intents.integration.repository import (
    IntentContextRepository,
    default_context_repository,
)
from app.domain.intents.integration.schemas import (
    DashboardIntentContextDTO,
    ExecutiveIntentDTO,
    IntentIntelligenceContextDTO,
    StandardAPIIntentContextDTO,
    StructuredIntentContextDTO,
)
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentIntelligencePlatform:
    """
    The Unified Intent Intelligence Platform.
    Root container encapsulating Gateway, Assembler, Query, Export, Composition, and Registry.
    """

    def __init__(
        self,
        repository: Optional[IntentContextRepository] = None,
        cache: Optional[IIntentContextCache] = None,
        registry: Optional[IntentContextRegistry] = None,
    ) -> None:
        self.repository = repository or default_context_repository
        self.cache = cache or NullIntentContextCache()
        self.registry = registry or default_context_registry

        self.assembler = IntentContextAssembler()
        self.pipeline = IntentIntegrationPipeline()
        self.query_engine = IntentQueryEngine(repository=self.repository, cache=self.cache)
        self.export_engine = IntentExportEngine()
        self.composition_engine = IntentCompositionEngine(assembler=self.assembler, registry=self.registry)

        self.gateway = IntentIntelligenceGateway(
            pipeline=self.pipeline,
            assembler=self.assembler,
            query_engine=self.query_engine,
            export_engine=self.export_engine,
            composition_engine=self.composition_engine,
            repository=self.repository,
            cache=self.cache,
            registry=self.registry,
        )

    # ── High-Level Assembly Methods ───────────────────────────────────────────

    def build_context(
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
        """Assembles and persists an IntentIntelligenceContext."""
        return self.gateway.integrate(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            profile=profile,
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

    def get_executive_context(self, conversation_id: str) -> Optional[ExecutiveIntentContext]:
        ctx = self.gateway.get_context(conversation_id, profile=CompositionProfileType.EXECUTIVE)
        return ctx.executive_view if ctx else None

    def get_sales_context(self, conversation_id: str) -> Optional[SalesIntentContext]:
        ctx = self.gateway.get_context(conversation_id, profile=CompositionProfileType.SALES)
        return ctx.sales_view if ctx else None

    def get_operations_context(self, conversation_id: str) -> Optional[OperationsIntentContext]:
        ctx = self.gateway.get_context(conversation_id, profile=CompositionProfileType.OPERATIONS)
        return ctx.operations_view if ctx else None

    def get_audit_context(self, conversation_id: str) -> Optional[AuditIntentContext]:
        ctx = self.gateway.get_context(conversation_id, profile=CompositionProfileType.AUDIT)
        return ctx.audit_view if ctx else None

    def get_custom_context(self, conversation_id: str) -> Optional[CustomIntentContext]:
        ctx = self.gateway.get_context(conversation_id, profile=CompositionProfileType.CUSTOM)
        return ctx.custom_view if ctx else None

    # ── Export Methods ────────────────────────────────────────────────────────

    def export_dashboard(self, conversation_id: str) -> Optional[DashboardIntentContextDTO]:
        ctx = self.gateway.get_context(conversation_id)
        if not ctx:
            return None
        return self.export_engine.to_dashboard_dto(ctx)

    def export_executive(self, conversation_id: str) -> Optional[ExecutiveIntentDTO]:
        ctx = self.gateway.get_context(conversation_id)
        if not ctx:
            return None
        return self.export_engine.to_executive_dto(ctx)

    def export_structured(self, conversation_id: str) -> Optional[StructuredIntentContextDTO]:
        ctx = self.gateway.get_context(conversation_id)
        if not ctx:
            return None
        return self.export_engine.to_structured_dto(ctx)

    def export_standard_api(self, conversation_id: str) -> Optional[StandardAPIIntentContextDTO]:
        ctx = self.gateway.get_context(conversation_id)
        if not ctx:
            return None
        return self.export_engine.to_standard_api_dto(ctx)

    def export_full_dto(self, conversation_id: str) -> Optional[IntentIntelligenceContextDTO]:
        ctx = self.gateway.get_context(conversation_id)
        if not ctx:
            return None
        return self.export_engine.to_full_dto(ctx)

    # ── Plugin Extensions ─────────────────────────────────────────────────────

    def register_plugin(self, plugin: IntentIntelligencePlugin) -> None:
        self.registry.register_plugin(plugin)


# Global default platform instance
default_intent_platform = IntentIntelligencePlatform()
