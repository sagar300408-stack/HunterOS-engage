"""
HunterOS Engage — Graph Traversal Engine (Phase 2.1.4)

Orchestrates multi-hop graph traversals, neighborhood exploration,
shortest / weighted pathfinding, and hierarchical tree generation.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Set

from app.domain.memory.graph.models import (
    EntityReference,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipType,
)
from app.domain.memory.graph.repository import GraphReadRepository
from app.domain.memory.graph.schemas import (
    EntityReferenceDTO,
    EntityRelationshipResponse,
    GraphTreeNode,
    PathFindingResponse,
)
from app.domain.memory.graph.traversal.strategies import (
    BreadthFirstTraversal,
    DepthFirstTraversal,
    ShortestPathTraversal,
    TraversalResult,
    TraversalStrategy,
    WeightedTraversal,
)


class GraphTraversalEngine:
    """
    High-level traversal engine delegating to pluggable TraversalStrategies.
    Reads graph state via GraphReadRepository.
    """

    def __init__(self, read_repository: GraphReadRepository) -> None:
        self._read_repo = read_repository
        self._strategies: Dict[str, TraversalStrategy] = {
            "bfs": BreadthFirstTraversal(),
            "dfs": DepthFirstTraversal(),
            "shortest_path": ShortestPathTraversal(),
            "weighted": WeightedTraversal(),
        }

    def register_strategy(self, name: str, strategy: TraversalStrategy) -> None:
        """Register custom traversal strategy."""
        self._strategies[name.lower()] = strategy

    async def get_direct_relationships(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: GraphNodeType | str,
        entity_id: str,
        direction: str = "ALL",
        relationship_types: Optional[List[RelationshipType | str]] = None,
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Fetch immediate 1-hop incident relationships with optional filtering."""
        type_str = entity_type.value if hasattr(entity_type, "value") else str(entity_type)
        edges = await self._read_repo.get_incident_edges(
            workspace_id=workspace_id,
            entity_type=type_str,
            entity_id=entity_id,
            direction=direction,
            session=session,
        )

        rel_type_filter = (
            {t.value if hasattr(t, "value") else str(t) for t in relationship_types}
            if relationship_types
            else None
        )

        filtered = []
        for edge in edges:
            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            if rel_type_filter and rel_type not in rel_type_filter:
                continue
            if edge.strength < min_strength:
                continue
            if edge.metadata.confidence < min_confidence:
                continue
            filtered.append(edge)

        return filtered

    async def traverse_neighbors(
        self,
        workspace_id: Optional[uuid.UUID],
        start_entity_type: GraphNodeType | str,
        start_entity_id: str,
        max_depth: int = 2,
        strategy_name: str = "bfs",
        relationship_types: Optional[List[RelationshipType | str]] = None,
        direction: str = "ALL",
        min_strength: float = 0.0,
        min_confidence: float = 0.0,
        limit: int = 200,
        session: Any = None,
    ) -> TraversalResult:
        """Traverse graph up to max_depth hops using specified traversal strategy."""
        all_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )

        strat = self._strategies.get(strategy_name.lower(), self._strategies["bfs"])
        type_str = start_entity_type.value if hasattr(start_entity_type, "value") else str(start_entity_type)
        start_key = f"{type_str}:{start_entity_id}"

        allowed_types = (
            {t.value if hasattr(t, "value") else str(t) for t in relationship_types}
            if relationship_types
            else None
        )

        return strat.execute(
            edges=all_edges,
            start_key=start_key,
            max_depth=max_depth,
            allowed_types=allowed_types,
            min_strength=min_strength,
            min_confidence=min_confidence,
            direction=direction,
            limit=limit,
        )

    async def find_path(
        self,
        workspace_id: Optional[uuid.UUID],
        source_entity_type: GraphNodeType | str,
        source_entity_id: str,
        target_entity_type: GraphNodeType | str,
        target_entity_id: str,
        max_depth: int = 5,
        weighted: bool = False,
        min_confidence: float = 0.0,
        session: Any = None,
    ) -> PathFindingResponse:
        """Discover shortest or weighted path connecting two business entities."""
        all_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )

        s_type = source_entity_type.value if hasattr(source_entity_type, "value") else str(source_entity_type)
        t_type = target_entity_type.value if hasattr(target_entity_type, "value") else str(target_entity_type)
        start_key = f"{s_type}:{source_entity_id}"
        target_key = f"{t_type}:{target_entity_id}"

        strat = self._strategies["weighted"] if weighted else self._strategies["shortest_path"]
        res = strat.execute(
            edges=all_edges,
            start_key=start_key,
            target_key=target_key,
            max_depth=max_depth,
            min_confidence=min_confidence,
        )

        if not res.edges and start_key != target_key:
            return PathFindingResponse(
                found=False,
                total_hops=0,
                path_nodes=[],
                path_edges=[],
                total_cost=0.0,
            )

        node_dtos = [
            EntityReferenceDTO(
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                workspace_id=n.workspace_id,
                label=n.label,
                properties=n.properties,
            )
            for n in res.nodes
        ]

        edge_dtos = [
            EntityRelationshipResponse(
                relationship_id=e.id,
                workspace_id=e.workspace_id,
                source=EntityReferenceDTO(
                    entity_type=e.source.entity_type,
                    entity_id=e.source.entity_id,
                    workspace_id=e.source.workspace_id,
                    label=e.source.label,
                    properties=e.source.properties,
                ),
                target=EntityReferenceDTO(
                    entity_type=e.target.entity_type,
                    entity_id=e.target.entity_id,
                    workspace_id=e.target.workspace_id,
                    label=e.target.label,
                    properties=e.target.properties,
                ),
                relationship_type=e.relationship_type,
                direction=e.direction,
                strength=e.strength,
                status=e.status,
                metadata=e.metadata.to_dict(),
                version=e.version,
                is_deleted=e.is_deleted,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in res.edges
        ]

        return PathFindingResponse(
            found=True,
            total_hops=len(res.edges),
            path_nodes=node_dtos,
            path_edges=edge_dtos,
            total_cost=res.total_cost,
        )

    async def build_relationship_tree(
        self,
        workspace_id: Optional[uuid.UUID],
        root_entity_type: GraphNodeType | str,
        root_entity_id: str,
        max_depth: int = 3,
        relationship_types: Optional[List[RelationshipType | str]] = None,
        direction: str = "OUTGOING",
        session: Any = None,
    ) -> GraphTreeNode:
        """Generate a hierarchical tree rooted at the specified entity node."""
        all_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )

        r_type = root_entity_type if isinstance(root_entity_type, GraphNodeType) else GraphNodeType(root_entity_type)
        root_ref = EntityReference(
            entity_type=r_type,
            entity_id=root_entity_id,
            workspace_id=workspace_id,
        )

        # Build adjacency mapping
        allowed_types = (
            {t.value if hasattr(t, "value") else str(t) for t in relationship_types}
            if relationship_types
            else None
        )

        adj: Dict[str, List[Tuple[EntityReference, RelationshipAggregate]]] = {}
        for edge in all_edges:
            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            if allowed_types and rel_type not in allowed_types:
                continue

            u = edge.source.key
            v = edge.target.key

            if direction.upper() in ("OUTGOING", "ALL"):
                adj.setdefault(u, []).append((edge.target, edge))
            if direction.upper() in ("INCOMING", "ALL"):
                adj.setdefault(v, []).append((edge.source, edge))

        def _build_subtree(
            curr_ref: EntityReference,
            parent_edge: Optional[RelationshipAggregate],
            current_depth: int,
            visited_path: Set[str],
        ) -> GraphTreeNode:
            edge_dto = None
            if parent_edge:
                edge_dto = EntityRelationshipResponse(
                    relationship_id=parent_edge.id,
                    workspace_id=parent_edge.workspace_id,
                    source=EntityReferenceDTO(
                        entity_type=parent_edge.source.entity_type,
                        entity_id=parent_edge.source.entity_id,
                        workspace_id=parent_edge.source.workspace_id,
                        label=parent_edge.source.label,
                        properties=parent_edge.source.properties,
                    ),
                    target=EntityReferenceDTO(
                        entity_type=parent_edge.target.entity_type,
                        entity_id=parent_edge.target.entity_id,
                        workspace_id=parent_edge.target.workspace_id,
                        label=parent_edge.target.label,
                        properties=parent_edge.target.properties,
                    ),
                    relationship_type=parent_edge.relationship_type,
                    direction=parent_edge.direction,
                    strength=parent_edge.strength,
                    status=parent_edge.status,
                    metadata=parent_edge.metadata.to_dict(),
                    version=parent_edge.version,
                    is_deleted=parent_edge.is_deleted,
                    created_at=parent_edge.created_at,
                    updated_at=parent_edge.updated_at,
                )

            tree_node = GraphTreeNode(
                node=EntityReferenceDTO(
                    entity_type=curr_ref.entity_type,
                    entity_id=curr_ref.entity_id,
                    workspace_id=curr_ref.workspace_id,
                    label=curr_ref.label,
                    properties=curr_ref.properties,
                ),
                edge_to_parent=edge_dto,
                depth=current_depth,
                children=[],
            )

            if current_depth >= max_depth:
                return tree_node

            new_visited = visited_path | {curr_ref.key}
            for child_ref, child_edge in adj.get(curr_ref.key, []):
                if child_ref.key not in new_visited:
                    child_tree = _build_subtree(
                        child_ref,
                        child_edge,
                        current_depth + 1,
                        new_visited,
                    )
                    tree_node.children.append(child_tree)

            return tree_node

        return _build_subtree(root_ref, None, 0, set())


__all__ = [
    "GraphTraversalEngine",
]
