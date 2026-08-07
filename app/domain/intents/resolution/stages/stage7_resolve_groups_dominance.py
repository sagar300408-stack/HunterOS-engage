"""
HunterOS Engage V1 - Stage 7: Resolve Groups and Dominance
Clusters related intents into resolution groups and deterministically elects dominant intents.
"""

from __future__ import annotations

from collections import defaultdict
import time
from typing import Dict, List, Optional, Set
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.composite import CompositeDominanceStrategy
from app.domain.intents.resolution.models import (
    DominantIntent,
    IntentConflictSeverity,
    IntentNode,
    IntentResolutionGraph,
    IntentResolutionGroup,
    ResolutionStatus,
)
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry


class Stage7_ResolveGroupsAndDominance:
    """
    Stage 7: Forms coherent resolution groups from connected components / clusters
    and evaluates dominance strategies.
    """

    def __init__(self, registry: Optional[IntentResolutionRegistry] = None) -> None:
        self.registry = registry or default_resolution_registry

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        nodes = list(context.normalized_nodes.values())
        graph = context.resolution_graph

        if not nodes:
            context.resolved_groups = []
            context.dominant_intents = []
            duration = (time.perf_counter() - start) * 1000.0
            context.record_stage_timing("Stage7_ResolveGroupsAndDominance", duration)
            return

        # 1. Cluster nodes by connected components based on relationships & dependencies
        adj: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
        for r in context.analyzed_relationships:
            adj[r.source_intent_id].add(r.target_intent_id)
            adj[r.target_intent_id].add(r.source_intent_id)

        for d in context.analyzed_dependencies:
            adj[d.source_intent_id].add(d.target_intent_id)
            adj[d.target_intent_id].add(d.source_intent_id)

        # Also connect nodes in classification groups if available
        if context.classification_result:
            for g in getattr(context.classification_result, "groups", []):
                g_intents = getattr(g, "classified_intents", [])
                g_ids = [getattr(ci, "intent_id", None) for ci in g_intents if getattr(ci, "intent_id", None)]
                for i in range(len(g_ids)):
                    for j in range(i + 1, len(g_ids)):
                        if g_ids[i] in context.normalized_nodes and g_ids[j] in context.normalized_nodes:
                            adj[uuid.UUID(str(g_ids[i]))].add(uuid.UUID(str(g_ids[j])))
                            adj[uuid.UUID(str(g_ids[j]))].add(uuid.UUID(str(g_ids[i])))

        visited: Set[uuid.UUID] = set()
        clusters: List[List[IntentNode]] = []

        for node in nodes:
            if node.intent_id not in visited:
                cluster_nodes: List[IntentNode] = []
                queue = [node.intent_id]
                visited.add(node.intent_id)

                while queue:
                    curr_id = queue.pop(0)
                    curr_node = context.normalized_nodes.get(str(curr_id))
                    if curr_node:
                        cluster_nodes.append(curr_node)

                    for neighbor_id in adj.get(curr_id, set()):
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            queue.append(neighbor_id)

                clusters.append(cluster_nodes)

        # 2. Build CompositeDominanceStrategy from registered strategies
        strategies = self.registry.get_dominance_strategies()
        dominance_engine = CompositeDominanceStrategy(strategies=strategies)

        resolved_groups: List[IntentResolutionGroup] = []
        all_dominant_intents: List[DominantIntent] = []

        for cluster in clusters:
            all_ids = [c.intent_id for c in cluster]
            primary_cat = cluster[0].category if cluster else "GENERAL"

            # Elect Dominant Intent
            dominant: Optional[DominantIntent] = dominance_engine.resolve_dominant_intent(cluster, context)
            if dominant:
                all_dominant_intents.append(dominant)

            # Supporting intents are all cluster nodes except the dominant one
            dom_id = dominant.intent_id if dominant else None
            supporting = [c for c in cluster if c.intent_id != dom_id]

            # Filter conflicts & dependencies pertaining to this group
            cluster_id_set = set(all_ids)
            group_conflicts = [c for c in context.analyzed_conflicts if any(iid in cluster_id_set for iid in c.intent_ids)]
            group_deps = [d for d in context.analyzed_dependencies if d.source_intent_id in cluster_id_set or d.target_intent_id in cluster_id_set]

            # Build group subgraph
            group_nodes = {str(c.intent_id): c for c in cluster}
            group_edges = [e for e in context.analyzed_relationships if e.source_intent_id in cluster_id_set and e.target_intent_id in cluster_id_set]
            subgraph = IntentResolutionGraph(
                nodes=group_nodes,
                edges=group_edges,
                conflicts=group_conflicts,
                dependencies=group_deps,
            )

            # Determine Resolution Status
            if any(c.severity == IntentConflictSeverity.CRITICAL for c in group_conflicts):
                status = ResolutionStatus.UNRESOLVED_CONFLICT
            elif len(group_conflicts) > 0:
                status = ResolutionStatus.PARTIALLY_RESOLVED
            elif len(cluster) == 1:
                status = ResolutionStatus.INDEPENDENT
            else:
                status = ResolutionStatus.RESOLVED

            ev_ids = set()
            for c in cluster:
                ev_ids.update(c.evidence_message_ids)

            group_name = f"{primary_cat}_{dominant.canonical_name if dominant else 'GROUP'}"

            res_group = IntentResolutionGroup(
                name=group_name,
                group_type=primary_cat,
                dominant_intent=dominant,
                supporting_intents=supporting,
                all_intent_ids=all_ids,
                subgraph=subgraph,
                conflicts=group_conflicts,
                dependencies=group_deps,
                resolution_status=status,
                evidence_message_ids=list(ev_ids),
                metadata={"cluster_size": len(cluster)},
            )
            resolved_groups.append(res_group)

        context.resolved_groups = resolved_groups
        context.dominant_intents = all_dominant_intents

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage7_ResolveGroupsAndDominance", duration)
