"""
HunterOS Engage V1 - Executive Resolution View
Strategic high-level portfolio overview of multi-intent complexity, dominant intents, and conflict health.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.resolution.models import MultiIntentResolutionResult, ResolutionStatus
from app.domain.intents.resolution.views.base import BaseResolutionView


class ExecutiveResolutionView(BaseResolutionView):
    """
    Renders high-level summary metrics for executive visibility.
    """

    def render(self, result: MultiIntentResolutionResult) -> Dict[str, Any]:
        total_intents = len(result.resolution_graph.nodes)
        total_groups = len(result.groups)
        total_conflicts = len(result.resolution_graph.conflicts)
        critical_conflicts = sum(1 for c in result.resolution_graph.conflicts if c.severity.value == "CRITICAL")

        # Conflict health status
        if critical_conflicts > 0:
            health = "CRITICAL_ATTENTION_REQUIRED"
        elif total_conflicts > 0:
            health = "MODERATE_FRICTION"
        else:
            health = "CLEAR_AND_ALIGNED"

        # Complexity score [0.0 - 1.0] based on intent count, conflicts, and dependencies
        dep_count = len(result.resolution_graph.dependencies)
        complexity = min(1.0, (total_intents * 0.1 + total_conflicts * 0.2 + dep_count * 0.15) / 5.0)

        dominant_summary = [
            {
                "intent_id": str(d.intent_id),
                "name": d.canonical_name,
                "score": d.dominance_score,
                "primary_driver": d.primary_factor.value,
            }
            for d in result.dominant_intents
        ]

        group_status_breakdown = {}
        for g in result.groups:
            status_key = g.resolution_status.value
            group_status_breakdown[status_key] = group_status_breakdown.get(status_key, 0) + 1

        return {
            "view_type": "EXECUTIVE",
            "resolution_id": str(result.resolution_id),
            "entity_type": result.entity_type,
            "entity_id": result.entity_id,
            "conversation_id": result.conversation_id,
            "portfolio_health": health,
            "intent_complexity_score": round(complexity, 2),
            "summary_metrics": {
                "total_intents": total_intents,
                "total_resolution_groups": total_groups,
                "total_conflicts": total_conflicts,
                "critical_conflicts": critical_conflicts,
                "total_dependencies": dep_count,
            },
            "dominant_intents": dominant_summary,
            "group_status_breakdown": group_status_breakdown,
            "snapshot_id": str(result.snapshot.graph_snapshot_id),
            "generated_at": result.generated_at.isoformat(),
        }
