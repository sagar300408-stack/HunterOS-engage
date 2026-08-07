"""
HunterOS Engage V1 - Intent Resolution API v1
Frozen public API contract for Multi-Intent Resolution.
Downstream modules must consume this API interface exclusively.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.engine import MultiIntentResolutionEngine
from app.domain.intents.resolution.repository import ResolutionRepository, default_resolution_repository
from app.domain.intents.resolution.schemas import (
    IntentResolutionAnalyticsDTO,
    IntentResolutionGraphDTO,
    MultiIntentResolutionResponse,
    ResolveIntentsRequest,
)
from app.domain.intents.resolution.views.audit import AuditResolutionView
from app.domain.intents.resolution.views.executive import ExecutiveResolutionView
from app.domain.intents.resolution.views.operations import OperationsResolutionView
from app.domain.intents.resolution.views.sales import SalesResolutionView

logger = logging.getLogger(__name__)


class IntentResolutionAPIv1:
    """
    Frozen Public API Surface for Intent Resolution (V1 Contract).
    Guarantees backward compatibility, strong typing, and isolated consumption.
    """

    def __init__(
        self,
        engine: Optional[MultiIntentResolutionEngine] = None,
        repository: Optional[ResolutionRepository] = None,
    ) -> None:
        self.repository = repository or default_resolution_repository
        self.engine = engine or MultiIntentResolutionEngine(repository=self.repository)

        # Pre-instantiate CQRS projection views
        self._views = {
            "EXECUTIVE": ExecutiveResolutionView(),
            "SALES": SalesResolutionView(),
            "OPERATIONS": OperationsResolutionView(),
            "AUDIT": AuditResolutionView(),
        }

    def resolve_intents(
        self,
        request: ResolveIntentsRequest,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insight: Optional[Any] = None,
    ) -> MultiIntentResolutionResponse:
        """
        Execute deterministic multi-intent resolution and return the frozen V1 response DTO.
        """
        entity_id = request.entity_id or request.customer_id or "ANONYMOUS"

        domain_result = self.engine.resolve(
            conversation_id=request.conversation_id,
            entity_id=entity_id,
            entity_type=request.entity_type,
            workspace_id=request.workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insight=conversation_insight,
            rule_pack_names=request.rule_pack_names,
            plugin_names=request.plugin_names,
            custom_parameters=request.custom_parameters,
            save_result=True,
        )

        return MultiIntentResolutionResponse.from_domain(domain_result)

    def get_resolution(self, resolution_id: uuid.UUID) -> Optional[MultiIntentResolutionResponse]:
        """Fetch a resolution result by resolution_id."""
        domain_result = self.repository.get_by_id(resolution_id)
        if not domain_result:
            return None
        return MultiIntentResolutionResponse.from_domain(domain_result)

    def get_latest_resolution(
        self,
        entity_type: str,
        entity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[MultiIntentResolutionResponse]:
        """Fetch the latest resolution result for a specific entity."""
        domain_result = self.repository.get_latest_by_entity(entity_type, entity_id, workspace_id)
        if not domain_result:
            return None
        return MultiIntentResolutionResponse.from_domain(domain_result)

    def get_resolution_graph_dto(self, resolution_id: uuid.UUID) -> Optional[IntentResolutionGraphDTO]:
        """Fetch strictly the public graph representation (User Directive 8)."""
        domain_result = self.repository.get_by_id(resolution_id)
        if not domain_result:
            return None
        return IntentResolutionGraphDTO.from_domain(domain_result.resolution_graph)

    def get_analytics(self, resolution_id: uuid.UUID) -> Optional[IntentResolutionAnalyticsDTO]:
        """Fetch resolution analytics metrics for a given resolution (User Directive 6)."""
        res_dto = self.get_resolution(resolution_id)
        if not res_dto:
            return None
        return res_dto.analytics

    def get_view(
        self,
        resolution_id: uuid.UUID,
        view_name: str = "EXECUTIVE",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a role-specific projection view (EXECUTIVE, SALES, OPERATIONS, AUDIT)."""
        domain_result = self.repository.get_by_id(resolution_id)
        if not domain_result:
            return None

        view_handler = self._views.get(view_name.upper())
        if not view_handler:
            raise ValueError(f"Unknown view '{view_name}'. Supported views: {list(self._views.keys())}")

        return view_handler.render(domain_result)


# Global singleton instance
intent_resolution_api_v1 = IntentResolutionAPIv1()
