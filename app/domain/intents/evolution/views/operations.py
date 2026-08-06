"""
HunterOS Engage V1 - Operations Evolution View
Operational perspective tracking fulfillment, scheduling, support persistence, and bottlenecks.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.domain.intents.evolution.models import (
    IntentEvolutionResult,
    IntentLifecycleState,
)
from app.domain.intents.evolution.views.base import AbstractEvolutionView


class OperationsEvolutionView(AbstractEvolutionView):
    """
    Operations view focusing on operational fulfillment, support friction, and scheduling.
    """

    def __init__(self):
        super().__init__(view_name="operations")

    def project(self, result: IntentEvolutionResult) -> Dict[str, Any]:
        persisting_support: List[Dict[str, Any]] = []
        fulfillment_intents: List[Dict[str, Any]] = []

        for t in result.timelines:
            item = {
                "intent_id": str(t.intent_id),
                "intent_name": t.intent_name,
                "taxonomy_path": t.taxonomy_path,
                "lifecycle_state": t.current_lifecycle_state.value,
                "velocity": t.velocity.value,
                "frequency": t.observation_frequency,
                "conversations": t.source_conversations,
            }
            if t.current_lifecycle_state == IntentLifecycleState.PERSISTING:
                persisting_support.append(item)

            if any(
                term in t.taxonomy_path.upper() or term in t.intent_name.upper()
                for term in ("SUPPORT", "SERVICE", "APPOINTMENT", "SCHEDULE", "ISSUE", "FULFILLMENT")
            ):
                fulfillment_intents.append(item)

        return {
            "view": self.view_name,
            "entity_id": result.entity_id,
            "entity_type": result.entity_type.value,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "generated_at": result.generated_at.isoformat(),
            "persisting_operational_intents": persisting_support,
            "fulfillment_and_service_intents": fulfillment_intents,
            "total_operational_intents": len(fulfillment_intents),
        }
