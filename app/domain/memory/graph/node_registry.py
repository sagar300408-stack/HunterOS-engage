"""
HunterOS Engage — Node Registry & Node Handlers (Phase 2.1.4)

Provides dynamic registration, validation, and handler resolution for graph node types.
Avoids hardcoding enums and allows future modules / plugins to register custom node types.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Set, Type

from app.domain.memory.graph.models import (
    EntityReference,
    GraphNodeType,
    RelationshipType,
    RelationshipValidationError,
)


class AbstractNodeHandler(abc.ABC):
    """
    Abstract interface for node handlers.
    Each handler is responsible for a specific node type in the Knowledge Graph.
    """

    @property
    @abc.abstractmethod
    def node_type(self) -> GraphNodeType:
        """The node type handled by this handler."""
        raise NotImplementedError

    def validate_reference(self, ref: EntityReference) -> None:
        """
        Validate that the entity reference is valid for this node type.
        Raises RelationshipValidationError if invalid.
        """
        if not ref.entity_id or not str(ref.entity_id).strip():
            raise RelationshipValidationError(
                f"Invalid {self.node_type.value} reference: entity_id cannot be empty."
            )

    def resolve_label(self, ref: EntityReference) -> Optional[str]:
        """Resolve or generate a human-readable display label if missing."""
        if ref.label:
            return ref.label
        return f"{self.node_type.value} ({ref.entity_id})"

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        """Set of relationship types this node type is permitted to initiate (empty = all)."""
        return set()

    def allowed_incoming_relationships(self) -> Set[RelationshipType]:
        """Set of relationship types this node type is permitted to receive (empty = all)."""
        return set()


class CustomerNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.CUSTOMER

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.KNOWS,
            RelationshipType.INTERESTED_IN,
            RelationshipType.OWNS,
            RelationshipType.REFERRED_BY,
            RelationshipType.RELATED_TO,
            RelationshipType.MEMBER_OF,
            RelationshipType.CREATED,
            RelationshipType.CUSTOM,
        }


class CompanyNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.COMPANY

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.OWNS,
            RelationshipType.MANAGES,
            RelationshipType.RELATED_TO,
            RelationshipType.MEMBER_OF,
            RelationshipType.CUSTOM,
        }


class ContactNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.CONTACT

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.KNOWS,
            RelationshipType.WORKS_FOR,
            RelationshipType.DECISION_MAKER_FOR,
            RelationshipType.REFERRED_BY,
            RelationshipType.RELATED_TO,
            RelationshipType.CUSTOM,
        }


class PropertyNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.PROPERTY

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.RELATED_TO,
            RelationshipType.CUSTOM,
        }


class OpportunityNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.OPPORTUNITY

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.RELATED_TO,
            RelationshipType.ASSIGNED_TO,
            RelationshipType.CUSTOM,
        }


class LeadNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.LEAD

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.INTERESTED_IN,
            RelationshipType.REFERRED_BY,
            RelationshipType.RELATED_TO,
            RelationshipType.CUSTOM,
        }


class EmployeeNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.EMPLOYEE

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.WORKS_FOR,
            RelationshipType.MANAGES,
            RelationshipType.ASSIGNED_TO,
            RelationshipType.CREATED,
            RelationshipType.RELATED_TO,
            RelationshipType.CUSTOM,
        }


class ProjectNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.PROJECT

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.RELATED_TO,
            RelationshipType.ASSIGNED_TO,
            RelationshipType.CUSTOM,
        }


class DocumentNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.DOCUMENT

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return {
            RelationshipType.RELATED_TO,
            RelationshipType.CUSTOM,
        }


class CustomEntityNodeHandler(AbstractNodeHandler):
    @property
    def node_type(self) -> GraphNodeType:
        return GraphNodeType.CUSTOM

    def allowed_outgoing_relationships(self) -> Set[RelationshipType]:
        return set()  # Allow all for custom


class NodeRegistry:
    """
    Central registry for Knowledge Graph node types and their corresponding handlers.
    Provides extensibility for future plugins and custom business entities.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, AbstractNodeHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        defaults: List[AbstractNodeHandler] = [
            CustomerNodeHandler(),
            CompanyNodeHandler(),
            ContactNodeHandler(),
            PropertyNodeHandler(),
            OpportunityNodeHandler(),
            LeadNodeHandler(),
            EmployeeNodeHandler(),
            ProjectNodeHandler(),
            DocumentNodeHandler(),
            CustomEntityNodeHandler(),
        ]
        for handler in defaults:
            self.register_handler(handler)

    def register_handler(self, handler: AbstractNodeHandler) -> None:
        """Register a node handler for a given node type."""
        key = handler.node_type.value if hasattr(handler.node_type, "value") else str(handler.node_type)
        self._handlers[key.upper()] = handler

    def is_supported(self, node_type: GraphNodeType | str) -> bool:
        """Check if a node type has a registered handler."""
        key = node_type.value if hasattr(node_type, "value") else str(node_type)
        return key.upper() in self._handlers

    def get_handler(self, node_type: GraphNodeType | str) -> AbstractNodeHandler:
        """Retrieve handler for node type, fallback to CustomEntityNodeHandler."""
        key = node_type.value if hasattr(node_type, "value") else str(node_type)
        handler = self._handlers.get(key.upper())
        if not handler:
            handler = self._handlers.get("CUSTOM", CustomEntityNodeHandler())
        return handler

    def validate_node(self, ref: EntityReference) -> None:
        """Validate an entity reference using its registered handler."""
        handler = self.get_handler(ref.entity_type)
        handler.validate_reference(ref)

    def resolve_label(self, ref: EntityReference) -> Optional[str]:
        """Resolve display label for an entity reference."""
        handler = self.get_handler(ref.entity_type)
        return handler.resolve_label(ref)

    def get_registered_types(self) -> List[str]:
        """List all registered node type names."""
        return sorted(list(self._handlers.keys()))


# Global default registry
default_node_registry = NodeRegistry()

__all__ = [
    "AbstractNodeHandler",
    "CustomerNodeHandler",
    "CompanyNodeHandler",
    "ContactNodeHandler",
    "PropertyNodeHandler",
    "OpportunityNodeHandler",
    "LeadNodeHandler",
    "EmployeeNodeHandler",
    "ProjectNodeHandler",
    "DocumentNodeHandler",
    "CustomEntityNodeHandler",
    "NodeRegistry",
    "default_node_registry",
]
