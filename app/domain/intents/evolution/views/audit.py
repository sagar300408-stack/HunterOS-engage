"""
HunterOS Engage V1 - Audit Evolution View
Comprehensive audit trail containing complete immutable event stream, telemetry, and diagnostics.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.evolution.views.base import AbstractEvolutionView


class AuditEvolutionView(AbstractEvolutionView):
    """
    Audit view providing raw traceability, full event stream, and execution diagnostics.
    """

    def __init__(self):
        super().__init__(view_name="audit")

    def project(self, result: IntentEvolutionResult) -> Dict[str, Any]:
        return {
            "view": self.view_name,
            "evolution_id": str(result.evolution_id),
            "entity_id": result.entity_id,
            "entity_type": result.entity_type.value,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "current_conversation_id": result.current_conversation_id,
            "generated_at": result.generated_at.isoformat(),
            "event_stream": result.event_stream.to_dict(),
            "timelines_count": len(result.timelines),
            "histories_count": len(result.intent_histories),
            "metadata": result.metadata.to_dict(),
            "diagnostics": result.diagnostics.to_dict(),
        }
