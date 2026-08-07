"""
HunterOS Engage V1 - Operations Resolution View
Operational perspective highlighting operational dependencies, service bottlenecks, and technical support prerequisites.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.resolution.models import MultiIntentResolutionResult
from app.domain.intents.resolution.views.base import BaseResolutionView


class OperationsResolutionView(BaseResolutionView):
    """
    Renders operational intelligence detailing execution bottlenecks and service prerequisites.
    """

    def render(self, result: MultiIntentResolutionResult) -> Dict[str, Any]:
        operational_nodes = [
            n for n in result.resolution_graph.nodes.values()
            if n.category == "OPERATIONAL" or any(k in n.canonical_name.lower() for k in ("support", "auth", "bug", "outage", "setup", "integration", "billing"))
        ]

        # All Blocking Dependencies
        all_blockers = [
            {
                "dependency_id": str(d.dependency_id),
                "source_intent": result.resolution_graph.get_node(d.source_intent_id).canonical_name if result.resolution_graph.get_node(d.source_intent_id) else str(d.source_intent_id),
                "target_intent": result.resolution_graph.get_node(d.target_intent_id).canonical_name if result.resolution_graph.get_node(d.target_intent_id) else str(d.target_intent_id),
                "reason": d.reason,
            }
            for d in result.resolution_graph.dependencies
            if d.is_blocking
        ]

        # Resolution Groups Requiring Action
        action_groups = [
            {
                "group_id": str(g.group_id),
                "group_name": g.name,
                "status": g.resolution_status.value,
                "dominant_intent": g.dominant_intent.canonical_name if g.dominant_intent else None,
                "supporting_count": len(g.supporting_intents),
                "conflicts_count": len(g.conflicts),
            }
            for g in result.groups
            if g.resolution_status.value in ("UNRESOLVED_CONFLICT", "PARTIALLY_RESOLVED")
        ]

        return {
            "view_type": "OPERATIONS",
            "resolution_id": str(result.resolution_id),
            "entity_id": result.entity_id,
            "conversation_id": result.conversation_id,
            "operational_intents_count": len(operational_nodes),
            "blocking_dependencies": all_blockers,
            "unresolved_or_partial_groups": action_groups,
            "generated_at": result.generated_at.isoformat(),
        }
