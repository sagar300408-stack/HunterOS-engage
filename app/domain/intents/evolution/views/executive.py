"""
HunterOS Engage V1 - Executive Evolution View
High-level summary of intent momentum, velocity distribution, and resolution health.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.evolution.models import IntentEvolutionResult, IntentVelocity
from app.domain.intents.evolution.views.base import AbstractEvolutionView


class ExecutiveEvolutionView(AbstractEvolutionView):
    """
    Executive view providing strategic visibility into intent momentum and stability.
    """

    def __init__(self):
        super().__init__(view_name="executive")

    def project(self, result: IntentEvolutionResult) -> Dict[str, Any]:
        velocity_counts = {
            IntentVelocity.INCREASING.value: 0,
            IntentVelocity.DECREASING.value: 0,
            IntentVelocity.STABLE.value: 0,
            IntentVelocity.SPORADIC.value: 0,
            IntentVelocity.UNKNOWN.value: 0,
        }

        for t in result.timelines:
            v_val = t.velocity.value
            velocity_counts[v_val] = velocity_counts.get(v_val, 0) + 1

        top_intents = [
            {
                "intent_name": t.intent_name,
                "taxonomy_path": t.taxonomy_path,
                "lifecycle_state": t.current_lifecycle_state.value,
                "velocity": t.velocity.value,
                "frequency": t.observation_frequency,
                "confidence": t.current_confidence,
            }
            for t in sorted(result.timelines, key=lambda x: x.observation_frequency, reverse=True)[:5]
        ]

        return {
            "view": self.view_name,
            "entity_id": result.entity_id,
            "entity_type": result.entity_type.value,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "generated_at": result.generated_at.isoformat(),
            "summary": {
                "total_intents_tracked": len(result.timelines),
                "total_active_intents": result.metadata.total_active_intents,
                "total_persisting_intents": result.metadata.total_persisting_intents,
                "total_strengthening_intents": result.metadata.total_strengthening_intents,
                "total_weakening_intents": result.metadata.total_weakening_intents,
                "total_resolved_intents": result.metadata.total_resolved_intents,
                "total_closed_intents": result.metadata.total_closed_intents,
            },
            "velocity_distribution": velocity_counts,
            "top_intents": top_intents,
        }
