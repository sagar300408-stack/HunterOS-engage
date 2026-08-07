"""
HunterOS Engage V1 - Sales Resolution View
Commercial perspective highlighting revenue-driving intents, blockers, and purchase prerequisites.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.domain.intents.resolution.models import MultiIntentResolutionResult
from app.domain.intents.resolution.views.base import BaseResolutionView


class SalesResolutionView(BaseResolutionView):
    """
    Renders commercial intelligence focusing on purchasing intents, blockers, and dependencies.
    """

    def render(self, result: MultiIntentResolutionResult) -> Dict[str, Any]:
        commercial_nodes = [
            n for n in result.resolution_graph.nodes.values()
            if n.category == "COMMERCIAL" or any(k in n.canonical_name.lower() for k in ("pricing", "demo", "buy", "contract", "quote", "renew", "upgrade"))
        ]

        # Commercial Dominant Intents
        commercial_dominant = [
            d for d in result.dominant_intents
            if any(cn.intent_id == d.intent_id for cn in commercial_nodes)
        ]

        # Blocking Dependencies affecting Commercial Intents
        commercial_ids = {n.intent_id for n in commercial_nodes}
        commercial_blockers = [
            {
                "dependency_id": str(d.dependency_id),
                "prerequisite_intent": result.resolution_graph.get_node(d.source_intent_id).canonical_name if result.resolution_graph.get_node(d.source_intent_id) else str(d.source_intent_id),
                "blocked_commercial_intent": result.resolution_graph.get_node(d.target_intent_id).canonical_name if result.resolution_graph.get_node(d.target_intent_id) else str(d.target_intent_id),
                "is_blocking": d.is_blocking,
                "reason": d.reason,
            }
            for d in result.resolution_graph.dependencies
            if d.target_intent_id in commercial_ids and d.is_blocking
        ]

        # Commercial Conflicts (e.g. churn / mutually exclusive)
        commercial_conflicts = [
            {
                "conflict_id": str(c.conflict_id),
                "conflict_type": c.conflict_type.value,
                "severity": c.severity.value,
                "description": c.description,
                "resolution_hint": c.resolution_hint,
            }
            for c in result.resolution_graph.conflicts
            if any(iid in commercial_ids for iid in c.intent_ids)
        ]

        return {
            "view_type": "SALES",
            "resolution_id": str(result.resolution_id),
            "entity_id": result.entity_id,
            "conversation_id": result.conversation_id,
            "total_commercial_intents": len(commercial_nodes),
            "commercial_dominant_intents": [
                {
                    "intent_id": str(d.intent_id),
                    "name": d.canonical_name,
                    "dominance_score": d.dominance_score,
                    "rationale": d.rationale,
                }
                for d in commercial_dominant
            ],
            "purchasing_blockers": commercial_blockers,
            "deal_conflicts": commercial_conflicts,
            "generated_at": result.generated_at.isoformat(),
        }
