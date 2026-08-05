"""
HunterOS Engage — Relationship Validation & Graph Integrity Engine (Phase 2.1.4)

Provides validation for graph relationships:
  - Duplicate edge prevention
  - Self-loop prevention
  - Circular reference (cycle) detection for hierarchical / DAG relationships
  - Node-type compatibility matrix validation
  - Cross-workspace tenant boundary enforcement
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set, Tuple

from app.domain.memory.graph.models import (
    CircularRelationshipError,
    CrossWorkspaceRelationshipError,
    DuplicateRelationshipError,
    EntityReference,
    GraphNodeType,
    IncompatibleNodeTypesError,
    RelationshipDirection,
    RelationshipStatus,
    RelationshipType,
    RelationshipValidationError,
)
from app.domain.memory.graph.node_registry import NodeRegistry, default_node_registry


# ── Hierarchical Relationship Types (Must be Acyclic / DAGs) ─────────────────

HIERARCHICAL_RELATIONSHIP_TYPES: Set[RelationshipType] = {
    RelationshipType.MANAGES,
    RelationshipType.REFERRED_BY,
    RelationshipType.WORKS_FOR,
}


# ── Compatibility Matrix ──────────────────────────────────────────────────────

COMPATIBILITY_RULES: Dict[RelationshipType, Tuple[Set[GraphNodeType], Set[GraphNodeType]]] = {
    RelationshipType.WORKS_FOR: (
        {GraphNodeType.CONTACT, GraphNodeType.EMPLOYEE, GraphNodeType.CUSTOMER, GraphNodeType.CUSTOM},
        {GraphNodeType.COMPANY, GraphNodeType.CUSTOM},
    ),
    RelationshipType.DECISION_MAKER_FOR: (
        {GraphNodeType.CONTACT, GraphNodeType.CUSTOMER, GraphNodeType.EMPLOYEE, GraphNodeType.CUSTOM},
        {GraphNodeType.COMPANY, GraphNodeType.OPPORTUNITY, GraphNodeType.PROJECT, GraphNodeType.CUSTOM},
    ),
    RelationshipType.OWNS: (
        {GraphNodeType.CUSTOMER, GraphNodeType.COMPANY, GraphNodeType.CONTACT, GraphNodeType.CUSTOM},
        {GraphNodeType.PROPERTY, GraphNodeType.DOCUMENT, GraphNodeType.COMPANY, GraphNodeType.PROJECT, GraphNodeType.CUSTOM},
    ),
    RelationshipType.INTERESTED_IN: (
        {GraphNodeType.CUSTOMER, GraphNodeType.LEAD, GraphNodeType.CONTACT, GraphNodeType.CUSTOM},
        {GraphNodeType.PROPERTY, GraphNodeType.OPPORTUNITY, GraphNodeType.PROJECT, GraphNodeType.CUSTOM},
    ),
    RelationshipType.MANAGES: (
        {GraphNodeType.EMPLOYEE, GraphNodeType.COMPANY, GraphNodeType.CONTACT, GraphNodeType.CUSTOM},
        {GraphNodeType.PROPERTY, GraphNodeType.PROJECT, GraphNodeType.EMPLOYEE, GraphNodeType.CUSTOM},
    ),
    RelationshipType.ASSIGNED_TO: (
        {GraphNodeType.OPPORTUNITY, GraphNodeType.PROJECT, GraphNodeType.LEAD, GraphNodeType.CUSTOMER, GraphNodeType.CUSTOM},
        {GraphNodeType.EMPLOYEE, GraphNodeType.CONTACT, GraphNodeType.CUSTOM},
    ),
    RelationshipType.CREATED: (
        {GraphNodeType.EMPLOYEE, GraphNodeType.CUSTOMER, GraphNodeType.CONTACT, GraphNodeType.CUSTOM},
        {GraphNodeType.DOCUMENT, GraphNodeType.OPPORTUNITY, GraphNodeType.PROJECT, GraphNodeType.CUSTOM},
    ),
}


class RelationshipValidator:
    """
    Validates relationships prior to creation or mutation.
    Ensures graph consistency, type safety, tenant isolation, and prevents cycles.
    """

    def __init__(self, node_registry: Optional[NodeRegistry] = None) -> None:
        self.node_registry = node_registry or default_node_registry

    def validate_relationship(
        self,
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        workspace_id: Optional[uuid.UUID] = None,
        existing_edges: Optional[List[Dict[str, Any]]] = None,
        allow_self_loops: bool = False,
    ) -> None:
        """
        Run full validation suite on candidate relationship.
        Raises RelationshipValidationError subclass if invalid.
        """
        # 1. Validate Node References
        self.node_registry.validate_node(source)
        self.node_registry.validate_node(target)

        # 2. Validate Tenant Workspace Boundaries
        self._validate_workspace_isolation(source, target, workspace_id)

        # 3. Validate Self-Loops
        self._validate_self_loop(source, target, allow_self_loops)

        # 4. Validate Node Type Compatibility
        self._validate_type_compatibility(source, target, relationship_type)

        # 5. Check Duplicate Active Edge
        if existing_edges:
            self._validate_duplicates(source, target, relationship_type, existing_edges)

        # 6. Cycle Detection for Hierarchical Relationships
        if relationship_type in HIERARCHICAL_RELATIONSHIP_TYPES and existing_edges:
            self._validate_no_cycles(source, target, relationship_type, existing_edges)

    def _validate_workspace_isolation(
        self,
        source: EntityReference,
        target: EntityReference,
        workspace_id: Optional[uuid.UUID],
    ) -> None:
        """Ensure source and target entities belong to the same workspace."""
        if workspace_id:
            if source.workspace_id and source.workspace_id != workspace_id:
                raise CrossWorkspaceRelationshipError(
                    f"Source entity workspace ({source.workspace_id}) does not match relationship workspace ({workspace_id})."
                )
            if target.workspace_id and target.workspace_id != workspace_id:
                raise CrossWorkspaceRelationshipError(
                    f"Target entity workspace ({target.workspace_id}) does not match relationship workspace ({workspace_id})."
                )
        if source.workspace_id and target.workspace_id and source.workspace_id != target.workspace_id:
            raise CrossWorkspaceRelationshipError(
                f"Cannot link entities across workspaces: source={source.workspace_id}, target={target.workspace_id}."
            )

    def _validate_self_loop(
        self,
        source: EntityReference,
        target: EntityReference,
        allow_self_loops: bool,
    ) -> None:
        """Prevent self-referential edges unless explicitly permitted."""
        if source.key == target.key and not allow_self_loops:
            raise RelationshipValidationError(
                f"Self-referential relationship is not allowed on entity {source.key}."
            )

    def _validate_type_compatibility(
        self,
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
    ) -> None:
        """Ensure source and target node types are valid for the relationship type."""
        rules = COMPATIBILITY_RULES.get(relationship_type)
        if not rules:
            return  # Open compatibility for KNOWS, RELATED_TO, CUSTOM, etc.

        allowed_sources, allowed_targets = rules
        if source.entity_type not in allowed_sources:
            raise IncompatibleNodeTypesError(
                f"Invalid source node type '{source.entity_type.value}' for relationship '{relationship_type.value}'. "
                f"Allowed sources: {[t.value for t in allowed_sources]}."
            )
        if target.entity_type not in allowed_targets:
            raise IncompatibleNodeTypesError(
                f"Invalid target node type '{target.entity_type.value}' for relationship '{relationship_type.value}'. "
                f"Allowed targets: {[t.value for t in allowed_targets]}."
            )

    def _validate_duplicates(
        self,
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        existing_edges: List[Dict[str, Any]],
    ) -> None:
        """Prevent creating duplicate active edges between identical source, target, and type."""
        rel_type_str = relationship_type.value if hasattr(relationship_type, "value") else str(relationship_type)
        for edge in existing_edges:
            if edge.get("is_deleted"):
                continue
            if edge.get("status") in (RelationshipStatus.DELETED.value, RelationshipStatus.ARCHIVED.value):
                continue
            e_src = edge.get("source_key")
            e_tgt = edge.get("target_key")
            e_type = edge.get("relationship_type")
            if e_src == source.key and e_tgt == target.key and e_type == rel_type_str:
                raise DuplicateRelationshipError(
                    f"Active relationship '{rel_type_str}' already exists between {source.key} and {target.key}."
                )

    def _validate_no_cycles(
        self,
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        existing_edges: List[Dict[str, Any]],
    ) -> None:
        """
        Check if adding directed edge source -> target creates a cycle in a DAG.
        If a path already exists from target -> source, adding source -> target creates a cycle.
        """
        rel_type_str = relationship_type.value if hasattr(relationship_type, "value") else str(relationship_type)

        # Build adjacency list for this relationship type
        adj: Dict[str, List[str]] = {}
        for edge in existing_edges:
            if edge.get("is_deleted"):
                continue
            if edge.get("relationship_type") != rel_type_str:
                continue
            u = edge.get("source_key")
            v = edge.get("target_key")
            if u and v:
                adj.setdefault(u, []).append(v)

        # Check if source is reachable from target via DFS
        visited: Set[str] = set()
        stack: List[str] = [target.key]

        while stack:
            curr = stack.pop()
            if curr == source.key:
                raise CircularRelationshipError(
                    f"Creating '{rel_type_str}' from {source.key} -> {target.key} would create a circular reference cycle."
                )
            if curr not in visited:
                visited.add(curr)
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        stack.append(neighbor)


# Global default validator
default_relationship_validator = RelationshipValidator()

__all__ = [
    "RelationshipValidator",
    "default_relationship_validator",
    "HIERARCHICAL_RELATIONSHIP_TYPES",
    "COMPATIBILITY_RULES",
]
