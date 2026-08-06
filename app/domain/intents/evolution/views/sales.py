"""
HunterOS Engage V1 - Sales Evolution View
Commercial trajectory view focusing on buying interest, pricing inquiry, and deal progression.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.domain.intents.evolution.models import (
    IntentEvolutionResult,
    IntentLifecycleState,
)
from app.domain.intents.evolution.views.base import AbstractEvolutionView


class SalesEvolutionView(AbstractEvolutionView):
    """
    Sales perspective highlighting commercial momentum, pricing inquiries, and objections.
    """

    def __init__(self):
        super().__init__(view_name="sales")

    def project(self, result: IntentEvolutionResult) -> Dict[str, Any]:
        strengthening_intents: List[Dict[str, Any]] = []
        commercial_intents: List[Dict[str, Any]] = []

        for t in result.timelines:
            item = {
                "intent_id": str(t.intent_id),
                "intent_name": t.intent_name,
                "taxonomy_path": t.taxonomy_path,
                "lifecycle_state": t.current_lifecycle_state.value,
                "velocity": t.velocity.value,
                "confidence": t.current_confidence,
                "frequency": t.observation_frequency,
                "conversations": t.source_conversations,
            }
            if t.current_lifecycle_state == IntentLifecycleState.STRENGTHENING:
                strengthening_intents.append(item)

            if any(
                term in t.taxonomy_path.upper() or term in t.intent_name.upper()
                for term in ("BUY", "PURCHASE", "PRICE", "PRICING", "QUOTE", "DEAL", "COMMERCIAL", "BOOKING")
            ):
                commercial_intents.append(item)

        return {
            "view": self.view_name,
            "entity_id": result.entity_id,
            "entity_type": result.entity_type.value,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "generated_at": result.generated_at.isoformat(),
            "strengthening_commercial_signals": strengthening_intents,
            "tracked_commercial_intents": commercial_intents,
            "total_commercial_signals": len(commercial_intents),
        }
