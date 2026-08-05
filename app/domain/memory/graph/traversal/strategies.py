"""
HunterOS Engage — Graph Traversal Strategies (Phase 2.1.4)

Pluggable traversal strategies (BFS, DFS, ShortestPath, Weighted) for
knowledge graph exploration, pathfinding, and neighborhood extraction.
"""

from __future__ import annotations

import abc
import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.memory.graph.models import (
    EntityReference,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipType,
)


@dataclass
class TraversalResult:
    """Standard output resulting from a graph traversal."""
    nodes: List[EntityReference] = field(default_factory=list)
    edges: List[RelationshipAggregate] = field(default_factory=list)
    depths: Dict[str, int] = field(default_factory=dict)
    paths: List[List[str]] = field(default_factory=list)
    total_cost: float = 0.0


class TraversalStrategy(abc.ABC):
    """Abstract interface for knowledge graph traversal algorithms."""

    @abc.abstractmethod
    def execute(
        self,
        edges: List[RelationshipAggregate],
        start_key: str,
        target_key: Optional[str] = None,
        max_depth: int = 3,
        allowed_types: Optional[Set[str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        direction: str = "ALL",
        limit: int = 500,
    ) -> TraversalResult:
        """Execute traversal strategy and return structured results."""
        raise NotImplementedError


def _build_adjacency_map(
    edges: List[RelationshipAggregate],
    allowed_types: Optional[Set[str]] = None,
    min_strength: float = 0.0,
    min_confidence: float = 0.0,
    direction: str = "ALL",
) -> Tuple[Dict[str, List[Tuple[str, RelationshipAggregate]]], Dict[str, EntityReference]]:
    """Build directed/undirected adjacency map and node index from edge list."""
    adj: Dict[str, List[Tuple[str, RelationshipAggregate]]] = {}
    node_map: Dict[str, EntityReference] = {}
    dir_upper = direction.upper()

    for edge in edges:
        if edge.is_deleted or edge.status.value != "ACTIVE":
            continue
        rel_type_str = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
        if allowed_types and rel_type_str not in allowed_types:
            continue
        if edge.strength < min_strength:
            continue
        if edge.metadata.confidence < min_confidence:
            continue

        u = edge.source.key
        v = edge.target.key
        node_map[u] = edge.source
        node_map[v] = edge.target

        is_bidirectional = edge.direction in (RelationshipDirection.BIDIRECTIONAL, RelationshipDirection.UNDIRECTED)

        if dir_upper in ("ALL", "OUTGOING"):
            adj.setdefault(u, []).append((v, edge))
        if dir_upper in ("ALL", "INCOMING"):
            adj.setdefault(v, []).append((u, edge))

        if is_bidirectional and dir_upper == "OUTGOING":
            adj.setdefault(v, []).append((u, edge))
        elif is_bidirectional and dir_upper == "INCOMING":
            adj.setdefault(u, []).append((v, edge))

    return adj, node_map


class BreadthFirstTraversal(TraversalStrategy):
    """
    Standard level-by-level BFS traversal exploring the neighborhood around a start node.
    """

    def execute(
        self,
        edges: List[RelationshipAggregate],
        start_key: str,
        target_key: Optional[str] = None,
        max_depth: int = 3,
        allowed_types: Optional[Set[str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        direction: str = "ALL",
        limit: int = 500,
    ) -> TraversalResult:
        adj, node_map = _build_adjacency_map(edges, allowed_types, min_strength, min_confidence, direction)

        visited: Set[str] = {start_key}
        depths: Dict[str, int] = {start_key: 0}
        collected_edges: List[RelationshipAggregate] = []
        queue: deque[Tuple[str, int]] = deque([(start_key, 0)])

        while queue and len(visited) < limit:
            curr, depth = queue.popleft()
            if depth >= max_depth:
                continue

            for neighbor, edge in adj.get(curr, []):
                if edge not in collected_edges:
                    collected_edges.append(edge)
                if neighbor not in visited:
                    visited.add(neighbor)
                    depths[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
                    if target_key and neighbor == target_key:
                        break

        collected_nodes = [node_map[k] for k in visited if k in node_map]
        return TraversalResult(nodes=collected_nodes, edges=collected_edges, depths=depths)


class DepthFirstTraversal(TraversalStrategy):
    """
    Standard DFS traversal for discovering deep relational branches.
    """

    def execute(
        self,
        edges: List[RelationshipAggregate],
        start_key: str,
        target_key: Optional[str] = None,
        max_depth: int = 3,
        allowed_types: Optional[Set[str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        direction: str = "ALL",
        limit: int = 500,
    ) -> TraversalResult:
        adj, node_map = _build_adjacency_map(edges, allowed_types, min_strength, min_confidence, direction)

        visited: Set[str] = {start_key}
        depths: Dict[str, int] = {start_key: 0}
        collected_edges: List[RelationshipAggregate] = []
        stack: List[Tuple[str, int]] = [(start_key, 0)]

        while stack and len(visited) < limit:
            curr, depth = stack.pop()
            if depth >= max_depth:
                continue

            for neighbor, edge in reversed(adj.get(curr, [])):
                if edge not in collected_edges:
                    collected_edges.append(edge)
                if neighbor not in visited:
                    visited.add(neighbor)
                    depths[neighbor] = depth + 1
                    stack.append((neighbor, depth + 1))
                    if target_key and neighbor == target_key:
                        break

        collected_nodes = [node_map[k] for k in visited if k in node_map]
        return TraversalResult(nodes=collected_nodes, edges=collected_edges, depths=depths)


class ShortestPathTraversal(TraversalStrategy):
    """
    Finds the shortest unweighted or hop-based path between start_key and target_key.
    """

    def execute(
        self,
        edges: List[RelationshipAggregate],
        start_key: str,
        target_key: Optional[str] = None,
        max_depth: int = 6,
        allowed_types: Optional[Set[str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        direction: str = "ALL",
        limit: int = 500,
    ) -> TraversalResult:
        if not target_key:
            return TraversalResult()

        adj, node_map = _build_adjacency_map(edges, allowed_types, min_strength, min_confidence, direction)

        queue: deque[Tuple[str, List[str], List[RelationshipAggregate]]] = deque(
            [(start_key, [start_key], [])]
        )
        visited: Set[str] = {start_key}

        while queue:
            curr, path_nodes, path_edges = queue.popleft()
            if len(path_nodes) - 1 > max_depth:
                continue

            if curr == target_key:
                nodes_list = [node_map[k] for k in path_nodes if k in node_map]
                return TraversalResult(
                    nodes=nodes_list,
                    edges=path_edges,
                    depths={k: i for i, k in enumerate(path_nodes)},
                    paths=[path_nodes],
                    total_cost=float(len(path_edges)),
                )

            for neighbor, edge in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path_nodes + [neighbor], path_edges + [edge]))

        return TraversalResult()


class WeightedTraversal(TraversalStrategy):
    """
    Dijkstra-based shortest path traversal weighted inversely by (strength * confidence).
    Stronger and more confident edges have lower path resistance/cost.
    """

    def execute(
        self,
        edges: List[RelationshipAggregate],
        start_key: str,
        target_key: Optional[str] = None,
        max_depth: int = 6,
        allowed_types: Optional[Set[str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        direction: str = "ALL",
        limit: int = 500,
    ) -> TraversalResult:
        if not target_key:
            return TraversalResult()

        adj, node_map = _build_adjacency_map(edges, allowed_types, min_strength, min_confidence, direction)

        # Priority Queue holds (total_cost, counter, curr_key, path_nodes, path_edges)
        counter = 0
        pq: List[Tuple[float, int, str, List[str], List[RelationshipAggregate]]] = [
            (0.0, counter, start_key, [start_key], [])
        ]
        min_costs: Dict[str, float] = {start_key: 0.0}

        while pq:
            cost, _, curr, path_nodes, path_edges = heapq.heappop(pq)
            if len(path_nodes) - 1 > max_depth:
                continue

            if curr == target_key:
                nodes_list = [node_map[k] for k in path_nodes if k in node_map]
                return TraversalResult(
                    nodes=nodes_list,
                    edges=path_edges,
                    depths={k: i for i, k in enumerate(path_nodes)},
                    paths=[path_nodes],
                    total_cost=round(cost, 4),
                )

            if cost > min_costs.get(curr, float("inf")):
                continue

            for neighbor, edge in adj.get(curr, []):
                # Edge weight: higher strength * confidence -> lower cost
                factor = max(0.01, edge.strength * edge.metadata.confidence)
                edge_cost = 1.0 / factor
                new_cost = cost + edge_cost

                if new_cost < min_costs.get(neighbor, float("inf")):
                    min_costs[neighbor] = new_cost
                    counter += 1
                    heapq.heappush(
                        pq,
                        (new_cost, counter, neighbor, path_nodes + [neighbor], path_edges + [edge]),
                    )

        return TraversalResult()


__all__ = [
    "TraversalResult",
    "TraversalStrategy",
    "BreadthFirstTraversal",
    "DepthFirstTraversal",
    "ShortestPathTraversal",
    "WeightedTraversal",
]
