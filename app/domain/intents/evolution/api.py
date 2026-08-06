"""
HunterOS Engage V1 - Frozen Public API: Intent Evolution API v1
Single entry point for all downstream bounded contexts (Journey, Recommendations, Dashboard).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.engine import (
    IntentEvolutionEngine,
    default_evolution_engine,
)
from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentEvolutionEventType,
    IntentEvolutionResult,
    IntentHistory,
    IntentTimeline,
)
from app.domain.intents.evolution.query import (
    IntentEvolutionQuery,
    default_evolution_query,
)
from app.domain.intents.evolution.views.audit import AuditEvolutionView
from app.domain.intents.evolution.views.executive import ExecutiveEvolutionView
from app.domain.intents.evolution.views.operations import OperationsEvolutionView
from app.domain.intents.evolution.views.sales import SalesEvolutionView
from app.domain.intents.models import IntentDetectionResult


class IntentEvolutionAPIv1:
    """
    Frozen Public API interface for Intent History & Evolution bounded context.
    External modules MUST interact through this interface exclusively.
    """

    def __init__(
        self,
        engine: Optional[IntentEvolutionEngine] = None,
        query: Optional[IntentEvolutionQuery] = None,
    ):
        self.engine = engine or default_evolution_engine
        self.query = query or default_evolution_query
        self._views = {
            "executive": ExecutiveEvolutionView(),
            "sales": SalesEvolutionView(),
            "operations": OperationsEvolutionView(),
            "audit": AuditEvolutionView(),
        }

    def evolve_intents(
        self,
        entity_id: str,
        current_conversation_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> IntentEvolutionResult:
        """Execute the deterministic 8-stage evolution pipeline."""
        return self.engine.evolve(
            entity_id=entity_id,
            current_conversation_id=current_conversation_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            timeline=timeline,
            conversation_metadata=conversation_metadata,
            persist=persist,
        )

    def get_intent_history(self, intent_id: uuid.UUID) -> Optional[IntentHistory]:
        """Fetch cumulative history for an intent."""
        return self.query.get_history(intent_id)

    def get_intent_timeline(self, intent_id: uuid.UUID) -> Optional[IntentTimeline]:
        """Fetch chronological timeline for an intent."""
        return self.query.get_timeline(intent_id)

    def get_entity_timelines(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> List[IntentTimeline]:
        """Fetch all timelines for an entity."""
        return self.query.get_entity_timelines(entity_id, entity_type, workspace_id)

    def get_current_intent_state(self, intent_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Fetch current state of an intent."""
        return self.query.get_current_intent_state(intent_id)

    def get_evolution_events(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        workspace_id: Optional[uuid.UUID] = None,
        intent_id: Optional[uuid.UUID] = None,
        event_type: Optional[IntentEvolutionEventType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[IntentEvolutionEvent]:
        """Query evolution events with filtering."""
        return self.query.get_events(
            entity_id=entity_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
            intent_id=intent_id,
            event_type=event_type,
            from_date=from_date,
            to_date=to_date,
        )

    def get_evolution_view(
        self,
        result: IntentEvolutionResult,
        perspective: str,
    ) -> Dict[str, Any]:
        """Project an IntentEvolutionResult into a perspective view ('executive', 'sales', 'operations', 'audit')."""
        view_handler = self._views.get(perspective.lower())
        if not view_handler:
            raise ValueError(f"Unknown evolution perspective: '{perspective}'. Supported: {list(self._views.keys())}")
        return view_handler.project(result)

    def get_analytics(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Get descriptive temporal analytics for an entity."""
        return self.query.get_analytics(entity_id, entity_type, workspace_id)


intent_evolution_api_v1 = IntentEvolutionAPIv1()
