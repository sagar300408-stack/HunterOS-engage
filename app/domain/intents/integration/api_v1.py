"""
HunterOS Engage V1 - Intent Intelligence API v1
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Frozen public API contract for Intent Intelligence.
Downstream modules (Customer Journey, Recommendations, Executive Dashboard, Analytics, External APIs)
must consume Intent Intelligence exclusively through this frozen contract.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.models import (
    CompositionProfileType,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.platform import (
    IntentIntelligencePlatform,
    default_intent_platform,
)
from app.domain.intents.integration.schemas import (
    AuditIntentContextDTO,
    CustomIntentContextDTO,
    DashboardIntentContextDTO,
    ExecutiveIntentContextDTO,
    ExecutiveIntentDTO,
    IntegrateIntentsRequest,
    IntentIntelligenceContextDTO,
    IntentIntelligenceResponse,
    OperationsIntentContextDTO,
    QueryIntentContextRequest,
    SalesIntentContextDTO,
    StandardAPIIntentContextDTO,
    StructuredIntentContextDTO,
)
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentIntelligenceAPIv1:
    """
    Frozen Public API Surface for Intent Intelligence (V1 Contract).
    Guarantees backward compatibility, strong typing, and isolated consumption for downstream systems.
    """

    def __init__(self, platform: Optional[IntentIntelligencePlatform] = None) -> None:
        self.platform = platform or default_intent_platform
        self.gateway = self.platform.gateway
        self.export_engine = self.platform.export_engine

    def integrate_intents(
        self,
        request: IntegrateIntentsRequest,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insights: Optional[Any] = None,
    ) -> IntentIntelligenceResponse:
        """Assembles and persists unified intent context via 7-stage pipeline."""
        context = self.platform.build_context(
            conversation_id=request.conversation_id,
            entity_id=request.entity_id,
            workspace_id=request.workspace_id,
            profile=request.profile,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insights=conversation_insights,
            custom_filters=request.custom_filters,
            options=request.options,
        )

        full_dto = self.export_engine.to_full_dto(context)
        return IntentIntelligenceResponse(
            success=context.diagnostics.is_valid,
            context_id=context.context_id,
            profile=context.metadata.composition_profile,
            context=full_dto,
            generated_at=context.metadata.created_at,
        )

    def get_full_intent_context(
        self,
        conversation_id: str,
        profile: Optional[CompositionProfileType] = None,
    ) -> Optional[IntentIntelligenceContextDTO]:
        """Retrieve full unified intent context for a given conversation."""
        ctx = self.gateway.get_context(conversation_id, profile=profile)
        if not ctx:
            return None
        return self.export_engine.to_full_dto(ctx)

    def get_executive_intent_context(self, conversation_id: str) -> Optional[ExecutiveIntentContextDTO]:
        """Retrieve strategic executive role perspective."""
        full = self.get_full_intent_context(conversation_id, profile=CompositionProfileType.EXECUTIVE)
        return full.executive_view if full else None

    def get_sales_intent_context(self, conversation_id: str) -> Optional[SalesIntentContextDTO]:
        """Retrieve sales and commercial role perspective."""
        full = self.get_full_intent_context(conversation_id, profile=CompositionProfileType.SALES)
        return full.sales_view if full else None

    def get_operations_intent_context(self, conversation_id: str) -> Optional[OperationsIntentContextDTO]:
        """Retrieve operational fulfillment role perspective."""
        full = self.get_full_intent_context(conversation_id, profile=CompositionProfileType.OPERATIONS)
        return full.operations_view if full else None

    def get_audit_intent_context(self, conversation_id: str) -> Optional[AuditIntentContextDTO]:
        """Retrieve complete audit trace perspective."""
        full = self.get_full_intent_context(conversation_id, profile=CompositionProfileType.AUDIT)
        return full.audit_view if full else None

    def get_custom_intent_context(self, conversation_id: str) -> Optional[CustomIntentContextDTO]:
        """Retrieve custom filtered perspective."""
        full = self.get_full_intent_context(conversation_id, profile=CompositionProfileType.CUSTOM)
        return full.custom_view if full else None

    def export_dashboard(self, conversation_id: str) -> Optional[DashboardIntentContextDTO]:
        return self.platform.export_dashboard(conversation_id)

    def export_executive(self, conversation_id: str) -> Optional[ExecutiveIntentDTO]:
        return self.platform.export_executive(conversation_id)

    def export_structured(self, conversation_id: str) -> Optional[StructuredIntentContextDTO]:
        return self.platform.export_structured(conversation_id)

    def export_standard_api(self, conversation_id: str) -> Optional[StandardAPIIntentContextDTO]:
        return self.platform.export_standard_api(conversation_id)

    def query_contexts(self, request: QueryIntentContextRequest) -> List[IntentIntelligenceContextDTO]:
        contexts = self.gateway.query_contexts(
            workspace_id=request.workspace_id,
            entity_id=request.entity_id,
            conversation_id=request.conversation_id,
            profile=request.profile,
            limit=request.limit,
            offset=request.offset,
        )
        return [self.export_engine.to_full_dto(c) for c in contexts]

    def get_intent_lineage(self, conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
        nodes = self.gateway.get_intent_lineage(conversation_id, intent_id)
        return [n.model_dump() for n in nodes]

    def get_intent_conflicts(self, conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
        nodes = self.gateway.get_intent_conflicts(conversation_id, intent_id)
        return [n.model_dump() for n in nodes]

    def get_intent_dependencies(self, conversation_id: str, intent_id: str) -> List[Dict[str, Any]]:
        nodes = self.gateway.get_intent_dependencies(conversation_id, intent_id)
        return [n.model_dump() for n in nodes]

    def list_profiles(self) -> List[Dict[str, Any]]:
        return self.platform.registry.list_profiles()

    def list_plugins(self) -> List[Dict[str, Any]]:
        return self.platform.registry.list_plugins()


# Global singleton instance
intent_intelligence_api_v1 = IntentIntelligenceAPIv1()
