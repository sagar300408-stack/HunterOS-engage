"""
HunterOS Engage — Graph Statistics & Topology Metrics Engine (Phase 2.1.4)

Computes graph-level metrics, topology statistics, density, path lengths,
and node degree centrality metrics for future Recommendation Intelligence.
"""

from __future__ import annotations

import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Set

from app.domain.memory.graph.models import (
    GraphNodeType,
    RelationshipAggregate,
    RelationshipStatus,
    RelationshipType,
)
from app.domain.memory.graph.repository import GraphReadRepository
from app.domain.memory.graph.schemas import GraphStatisticsResponse


class GraphStatisticsEngine:
    """
    Computes topology metrics, density, degree distributions, and centrality statistics.
    """

    def __init__(self, read_repository: GraphReadRepository) -> None:
        self._read_repo = read_repository

    async def compute_statistics(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> GraphStatisticsResponse:
        """Compute complete graph topology metrics for a workspace."""
        all_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )

        all_workspace_edges = await self._read_repo.query(
            workspace_id=workspace_id,
            include_deleted=True,
            limit=1000,
            session=session,
        )

        node_keys: Set[str] = set()
        node_types: Dict[str, int] = {}
        rel_types: Dict[str, int] = {}
        status_dist: Dict[str, int] = {}
        strength_bins: Dict[str, int] = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        conf_bins: Dict[str, int] = {
            "0.0-0.5": 0,
            "0.5-0.7": 0,
            "0.7-0.9": 0,
            "0.9-1.0": 0,
        }
        degree_map: Dict[str, int] = {}
        adj: Dict[str, Set[str]] = {}

        # Process all edges for status counts
        for edge in all_workspace_edges:
            s_val = edge.status.value if hasattr(edge.status, "value") else str(edge.status)
            status_dist[s_val] = status_dist.get(s_val, 0) + 1

        active_count = 0
        archived_count = status_dist.get(RelationshipStatus.ARCHIVED.value, 0)

        for edge in all_edges:
            active_count += 1
            src_key = edge.source.key
            tgt_key = edge.target.key
            node_keys.add(src_key)
            node_keys.add(tgt_key)

            src_type = edge.source.entity_type.value if hasattr(edge.source.entity_type, "value") else str(edge.source.entity_type)
            tgt_type = edge.target.entity_type.value if hasattr(edge.target.entity_type, "value") else str(edge.target.entity_type)
            node_types[src_type] = node_types.get(src_type, 0) + 1
            node_types[tgt_type] = node_types.get(tgt_type, 0) + 1

            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

            # Strength binning
            s = edge.strength
            if s <= 0.2:
                strength_bins["0.0-0.2"] += 1
            elif s <= 0.4:
                strength_bins["0.2-0.4"] += 1
            elif s <= 0.6:
                strength_bins["0.4-0.6"] += 1
            elif s <= 0.8:
                strength_bins["0.6-0.8"] += 1
            else:
                strength_bins["0.8-1.0"] += 1

            # Confidence binning
            c = edge.metadata.confidence
            if c <= 0.5:
                conf_bins["0.0-0.5"] += 1
            elif c <= 0.7:
                conf_bins["0.5-0.7"] += 1
            elif c <= 0.9:
                conf_bins["0.7-0.9"] += 1
            else:
                conf_bins["0.9-1.0"] += 1

            # Degrees
            degree_map[src_key] = degree_map.get(src_key, 0) + 1
            degree_map[tgt_key] = degree_map.get(tgt_key, 0) + 1

            adj.setdefault(src_key, set()).add(tgt_key)
            adj.setdefault(tgt_key, set()).add(src_key)

        n = len(node_keys)
        e = len(all_edges)

        # Graph density: e / (n * (n - 1)) for directed graphs
        density = 0.0
        if n > 1:
            density = round(e / (n * (n - 1)), 4)

        # Degree Centrality Metrics (normalized)
        centrality_metrics: Dict[str, float] = {}
        if n > 1:
            for k, deg in degree_map.items():
                centrality_metrics[k] = round(deg / (n - 1), 4)

        # Average Path Length (sampled BFS across nodes up to 50 nodes)
        avg_path_length: Optional[float] = None
        if n > 1 and n <= 100:
            total_dist = 0
            pair_count = 0
            nodes_list = list(node_keys)
            for i in range(len(nodes_list)):
                start = nodes_list[i]
                dists: Dict[str, int] = {start: 0}
                queue = deque([start])
                while queue:
                    curr = queue.popleft()
                    for nbr in adj.get(curr, set()):
                        if nbr not in dists:
                            dists[nbr] = dists[curr] + 1
                            queue.append(nbr)
                for j in range(i + 1, len(nodes_list)):
                    tgt = nodes_list[j]
                    if tgt in dists:
                        total_dist += dists[tgt]
                        pair_count += 1
            if pair_count > 0:
                avg_path_length = round(total_dist / pair_count, 2)

        return GraphStatisticsResponse(
            workspace_id=workspace_id,
            total_nodes=n,
            total_relationships=len(all_workspace_edges),
            active_relationships=active_count,
            archived_relationships=archived_count,
            relationship_type_distribution=rel_types,
            node_type_distribution=node_types,
            status_distribution=status_dist,
            graph_density=density,
            average_path_length=avg_path_length,
            relationship_strength_distribution=strength_bins,
            confidence_distribution=conf_bins,
            node_centrality_metrics=centrality_metrics,
        )


__all__ = [
    "GraphStatisticsEngine",
]
