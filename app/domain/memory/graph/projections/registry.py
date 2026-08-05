"""
HunterOS Engage — Graph Projection Registry & Concrete Projections (Phase 2.1.4)

Implements pluggable Graph Projections:
  1. Customer360Projection
  2. OrganizationProjection
  3. PropertyNetworkProjection
  4. OpportunityNetworkProjection
  5. CustomGraphProjection

Phase 3 dashboards and future intelligence modules can register additional projections.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Set

from app.domain.memory.graph.models import (
    EntityReference,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipType,
)
from app.domain.memory.graph.schemas import (
    Customer360Response,
    CustomGraphResponse,
    EntityReferenceDTO,
    EntityRelationshipResponse,
    OpportunityNetworkResponse,
    OrganizationResponse,
    PropertyNetworkResponse,
)


def _to_dto(ref: EntityReference) -> EntityReferenceDTO:
    return EntityReferenceDTO(
        entity_type=ref.entity_type,
        entity_id=str(ref.entity_id),
        workspace_id=ref.workspace_id,
        label=ref.label,
        properties=dict(ref.properties),
    )


def _to_edge_dto(edge: RelationshipAggregate) -> EntityRelationshipResponse:
    return EntityRelationshipResponse(
        relationship_id=edge.id,
        workspace_id=edge.workspace_id,
        source=_to_dto(edge.source),
        target=_to_dto(edge.target),
        relationship_type=edge.relationship_type,
        direction=edge.direction,
        strength=edge.strength,
        status=edge.status,
        metadata=edge.metadata.to_dict(),
        version=edge.version,
        is_deleted=edge.is_deleted,
        created_at=edge.created_at,
        updated_at=edge.updated_at,
    )


class AbstractGraphProjection(abc.ABC):
    """Abstract interface for knowledge graph projections."""

    @property
    @abc.abstractmethod
    def projection_name(self) -> str:
        """Unique identifier for this projection type."""
        raise NotImplementedError

    @abc.abstractmethod
    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> Any:
        """Generate structured projection response from graph edges."""
        raise NotImplementedError


class Customer360Projection(AbstractGraphProjection):
    """Customer-centric 360-degree knowledge graph projection."""

    @property
    def projection_name(self) -> str:
        return "customer_360"

    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> Customer360Response:
        root_key = root_entity.key
        incident_edges: List[RelationshipAggregate] = []
        node_map: Dict[str, EntityReference] = {root_key: root_entity}

        for edge in edges:
            if edge.is_deleted or edge.status.value != "ACTIVE":
                continue
            if edge.source.key == root_key or edge.target.key == root_key:
                incident_edges.append(edge)
                node_map[edge.source.key] = edge.source
                node_map[edge.target.key] = edge.target

        companies, contacts, properties, opps, leads, docs, customs = [], [], [], [], [], [], []

        for key, node in node_map.items():
            if key == root_key:
                continue
            dto = _to_dto(node)
            if node.entity_type == GraphNodeType.COMPANY:
                companies.append(dto)
            elif node.entity_type == GraphNodeType.CONTACT:
                contacts.append(dto)
            elif node.entity_type == GraphNodeType.PROPERTY:
                properties.append(dto)
            elif node.entity_type == GraphNodeType.OPPORTUNITY:
                opps.append(dto)
            elif node.entity_type == GraphNodeType.LEAD:
                leads.append(dto)
            elif node.entity_type == GraphNodeType.DOCUMENT:
                docs.append(dto)
            else:
                customs.append(dto)

        edge_dtos = [_to_edge_dto(e) for e in incident_edges]

        return Customer360Response(
            projection_version="1.0.0",
            customer=_to_dto(root_entity),
            companies=companies,
            contacts=contacts,
            properties=properties,
            opportunities=opps,
            leads=leads,
            documents=docs,
            custom_entities=customs,
            relationships=edge_dtos,
            total_connections=len(incident_edges),
        )


class OrganizationProjection(AbstractGraphProjection):
    """Company-centric organization chart and business network projection."""

    @property
    def projection_name(self) -> str:
        return "organization"

    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> OrganizationResponse:
        root_key = root_entity.key
        incident_edges: List[RelationshipAggregate] = []
        node_map: Dict[str, EntityReference] = {root_key: root_entity}

        parents, subs, employees, decision_makers, opps, projects = [], [], [], [], [], []

        for edge in edges:
            if edge.is_deleted or edge.status.value != "ACTIVE":
                continue
            is_src = edge.source.key == root_key
            is_tgt = edge.target.key == root_key
            if not (is_src or is_tgt):
                continue

            incident_edges.append(edge)
            other = edge.target if is_src else edge.source
            node_map[other.key] = other
            dto = _to_dto(other)

            if other.entity_type == GraphNodeType.EMPLOYEE:
                employees.append(dto)
            elif other.entity_type == GraphNodeType.CONTACT:
                if edge.relationship_type == RelationshipType.DECISION_MAKER_FOR:
                    decision_makers.append(dto)
                else:
                    employees.append(dto)
            elif other.entity_type == GraphNodeType.COMPANY:
                if is_src:
                    subs.append(dto)
                else:
                    parents.append(dto)
            elif other.entity_type == GraphNodeType.OPPORTUNITY:
                opps.append(dto)
            elif other.entity_type == GraphNodeType.PROJECT:
                projects.append(dto)

        edge_dtos = [_to_edge_dto(e) for e in incident_edges]

        return OrganizationResponse(
            projection_version="1.0.0",
            company=_to_dto(root_entity),
            parent_companies=parents,
            subsidiaries=subs,
            employees=employees,
            decision_makers=decision_makers,
            open_opportunities=opps,
            projects=projects,
            relationships=edge_dtos,
            total_members=len(employees) + len(decision_makers),
        )


class PropertyNetworkProjection(AbstractGraphProjection):
    """Property-centric network projection."""

    @property
    def projection_name(self) -> str:
        return "property_network"

    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> PropertyNetworkResponse:
        root_key = root_entity.key
        incident_edges: List[RelationshipAggregate] = []
        owners, prospects, agents, docs = [], [], [], []

        for edge in edges:
            if edge.is_deleted or edge.status.value != "ACTIVE":
                continue
            is_src = edge.source.key == root_key
            is_tgt = edge.target.key == root_key
            if not (is_src or is_tgt):
                continue

            incident_edges.append(edge)
            other = edge.target if is_src else edge.source
            dto = _to_dto(other)

            if edge.relationship_type == RelationshipType.OWNS:
                owners.append(dto)
            elif edge.relationship_type == RelationshipType.INTERESTED_IN:
                prospects.append(dto)
            elif edge.relationship_type == RelationshipType.MANAGES:
                agents.append(dto)
            elif other.entity_type == GraphNodeType.DOCUMENT:
                docs.append(dto)

        edge_dtos = [_to_edge_dto(e) for e in incident_edges]

        return PropertyNetworkResponse(
            projection_version="1.0.0",
            property_entity=_to_dto(root_entity),
            owners=owners,
            interested_prospects=prospects,
            managing_agents=agents,
            documents=docs,
            relationships=edge_dtos,
            total_connections=len(incident_edges),
        )


class OpportunityNetworkProjection(AbstractGraphProjection):
    """Opportunity/Deal-centric network projection."""

    @property
    def projection_name(self) -> str:
        return "opportunity_network"

    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> OpportunityNetworkResponse:
        root_key = root_entity.key
        incident_edges: List[RelationshipAggregate] = []
        buyers, sellers, dms, agents, properties = [], [], [], [], []

        for edge in edges:
            if edge.is_deleted or edge.status.value != "ACTIVE":
                continue
            is_src = edge.source.key == root_key
            is_tgt = edge.target.key == root_key
            if not (is_src or is_tgt):
                continue

            incident_edges.append(edge)
            other = edge.target if is_src else edge.source
            dto = _to_dto(other)

            if edge.relationship_type == RelationshipType.DECISION_MAKER_FOR:
                dms.append(dto)
            elif edge.relationship_type == RelationshipType.ASSIGNED_TO:
                agents.append(dto)
            elif other.entity_type == GraphNodeType.PROPERTY:
                properties.append(dto)
            elif other.entity_type in (GraphNodeType.CUSTOMER, GraphNodeType.LEAD):
                buyers.append(dto)
            elif other.entity_type == GraphNodeType.COMPANY:
                sellers.append(dto)

        edge_dtos = [_to_edge_dto(e) for e in incident_edges]

        return OpportunityNetworkResponse(
            projection_version="1.0.0",
            opportunity=_to_dto(root_entity),
            buyers=buyers,
            sellers=sellers,
            decision_makers=dms,
            assigned_agents=agents,
            linked_properties=properties,
            relationships=edge_dtos,
            total_connections=len(incident_edges),
        )


class CustomGraphProjection(AbstractGraphProjection):
    """Custom multi-hop graph projection rooted at any entity."""

    @property
    def projection_name(self) -> str:
        return "custom"

    def project(
        self,
        edges: List[RelationshipAggregate],
        root_entity: EntityReference,
        max_depth: int = 2,
    ) -> CustomGraphResponse:
        root_key = root_entity.key
        node_map: Dict[str, EntityReference] = {root_key: root_entity}
        incident_edges: List[RelationshipAggregate] = []

        for edge in edges:
            if edge.is_deleted or edge.status.value != "ACTIVE":
                continue
            incident_edges.append(edge)
            node_map[edge.source.key] = edge.source
            node_map[edge.target.key] = edge.target

        node_dtos = [_to_dto(n) for n in node_map.values()]
        edge_dtos = [_to_edge_dto(e) for e in incident_edges]

        return CustomGraphResponse(
            projection_version="1.0.0",
            root_entity=_to_dto(root_entity),
            nodes=node_dtos,
            relationships=edge_dtos,
            total_nodes=len(node_dtos),
            total_edges=len(edge_dtos),
        )


class GraphProjectionRegistry:
    """Registry maintaining available graph projection engines."""

    def __init__(self) -> None:
        self._projections: Dict[str, AbstractGraphProjection] = {}
        self._register_default_projections()

    def _register_default_projections(self) -> None:
        defaults: List[AbstractGraphProjection] = [
            Customer360Projection(),
            OrganizationProjection(),
            PropertyNetworkProjection(),
            OpportunityNetworkProjection(),
            CustomGraphProjection(),
        ]
        for p in defaults:
            self.register_projection(p)

    def register_projection(self, projection: AbstractGraphProjection) -> None:
        self._projections[projection.projection_name.lower()] = projection

    def get_projection(self, name: str) -> AbstractGraphProjection:
        proj = self._projections.get(name.lower())
        if not proj:
            proj = self._projections.get("custom", CustomGraphProjection())
        return proj

    def list_projections(self) -> List[str]:
        return sorted(list(self._projections.keys()))


default_projection_registry = GraphProjectionRegistry()

__all__ = [
    "AbstractGraphProjection",
    "Customer360Projection",
    "OrganizationProjection",
    "PropertyNetworkProjection",
    "OpportunityNetworkProjection",
    "CustomGraphProjection",
    "GraphProjectionRegistry",
    "default_projection_registry",
]
