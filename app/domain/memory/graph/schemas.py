"""
HunterOS Engage — Knowledge Graph Schemas & DTOs (Phase 2.1.4)

Pydantic DTOs for graph operations, queries, traversals, projections,
statistics, and visualization serializers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.memory.graph.models import (
    GraphNodeType,
    RelationshipDirection,
    RelationshipStatus,
    RelationshipType,
)


class EntityReferenceDTO(BaseModel):
    """Pydantic representation of an entity reference."""
    entity_type: GraphNodeType = Field(..., description="Node entity category")
    entity_id: str = Field(..., description="Unique entity identifier within its domain")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Workspace tenant UUID")
    label: Optional[str] = Field(None, description="Display name / title for UI rendering")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes / tags")

    @property
    def key(self) -> str:
        return f"{self.entity_type.value}:{self.entity_id}"


class RelationshipMetadataDTO(BaseModel):
    """Metadata detailing relationship origin, confidence, and verification."""
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score (e.g. 1.0 for CRM, 0.72 for CI)")
    source: str = Field("manual_entry", description="Source system or module (e.g., crm_import, conversation_intelligence)")
    created_by: Optional[str] = Field(None, description="Actor ID or username who authored the edge")
    last_verified: Optional[datetime] = Field(None, description="Timestamp when the edge was last validated")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Custom domain-specific edge attributes")


class EntityRelationshipCreateRequest(BaseModel):
    """Request payload to create a new graph relationship."""
    workspace_id: Optional[uuid.UUID] = Field(None, description="Tenant workspace ID")
    source: EntityReferenceDTO = Field(..., description="Source entity reference")
    target: EntityReferenceDTO = Field(..., description="Target entity reference")
    relationship_type: RelationshipType = Field(..., description="Semantic relationship type")
    direction: RelationshipDirection = Field(RelationshipDirection.DIRECTED, description="Edge direction")
    strength: float = Field(1.0, ge=0.0, le=1.0, description="Relationship weight/strength")
    metadata: Optional[RelationshipMetadataDTO] = Field(default_factory=RelationshipMetadataDTO, description="Edge metadata")


class EntityRelationshipUpdateRequest(BaseModel):
    """Request payload to update an existing relationship."""
    strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="New relationship weight")
    direction: Optional[RelationshipDirection] = Field(None, description="New directionality")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated confidence")
    last_verified: Optional[datetime] = Field(None, description="Validation timestamp")
    metadata_update: Optional[Dict[str, Any]] = Field(None, description="Extra metadata key-values to merge")
    updated_by: Optional[str] = Field(None, description="Actor performing the update")


class EntityRelationshipResponse(BaseModel):
    """Response representing a knowledge graph relationship."""
    relationship_id: uuid.UUID
    workspace_id: Optional[uuid.UUID]
    source: EntityReferenceDTO
    target: EntityReferenceDTO
    relationship_type: RelationshipType
    direction: RelationshipDirection
    strength: float
    status: RelationshipStatus
    metadata: RelationshipMetadataDTO
    version: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class RelationshipBulkCreateRequest(BaseModel):
    """Request payload to create multiple relationships in a batch."""
    relationships: List[EntityRelationshipCreateRequest] = Field(..., min_items=1, description="List of edges to create")


class RelationshipBulkCreateResponse(BaseModel):
    """Response after creating multiple relationships."""
    created_count: int
    relationship_ids: List[uuid.UUID]


class GraphQueryRequest(BaseModel):
    """Filter parameters for querying graph relationships."""
    workspace_id: Optional[uuid.UUID] = None
    entity_type: Optional[GraphNodeType] = None
    entity_id: Optional[str] = None
    relationship_types: Optional[List[RelationshipType]] = None
    statuses: Optional[List[RelationshipStatus]] = None
    min_strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    direction: Optional[RelationshipDirection] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class GraphTraversalRequest(BaseModel):
    """Parameters for multi-hop graph traversal."""
    workspace_id: Optional[uuid.UUID] = None
    start_entity_type: GraphNodeType
    start_entity_id: str
    max_depth: int = Field(2, ge=1, le=10, description="Max traversal depth / hops")
    relationship_types: Optional[List[RelationshipType]] = None
    direction: RelationshipDirection = Field(RelationshipDirection.DIRECTED)
    min_strength: float = Field(0.0, ge=0.0, le=1.0)
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    limit: int = Field(200, ge=1, le=1000)


class PathFindingRequest(BaseModel):
    """Parameters for finding shortest or weighted path between two entities."""
    workspace_id: Optional[uuid.UUID] = None
    source_entity_type: GraphNodeType
    source_entity_id: str
    target_entity_type: GraphNodeType
    target_entity_id: str
    max_depth: int = Field(5, ge=1, le=10)
    weighted: bool = Field(False, description="Whether to use edge strength / confidence as path cost weights")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)


class PathFindingResponse(BaseModel):
    """Response containing path(s) between nodes."""
    found: bool
    total_hops: int
    path_nodes: List[EntityReferenceDTO]
    path_edges: List[EntityRelationshipResponse]
    total_cost: float = 0.0


class TreeTraversalRequest(BaseModel):
    """Parameters for hierarchical tree generation."""
    workspace_id: Optional[uuid.UUID] = None
    root_entity_type: GraphNodeType
    root_entity_id: str
    max_depth: int = Field(3, ge=1, le=6)
    relationship_types: Optional[List[RelationshipType]] = None
    direction: RelationshipDirection = Field(RelationshipDirection.DIRECTED)


class GraphTreeNode(BaseModel):
    """Recursive tree node representation for hierarchical graph views."""
    node: EntityReferenceDTO
    edge_to_parent: Optional[EntityRelationshipResponse] = None
    depth: int = 0
    children: List["GraphTreeNode"] = Field(default_factory=list)


# Update forward refs
GraphTreeNode.update_forward_refs()


# ── Projections DTOs ──────────────────────────────────────────────────────────

class Customer360Response(BaseModel):
    """Customer-centric 360 Knowledge Graph projection."""
    projection_version: str = "1.0.0"
    customer: EntityReferenceDTO
    companies: List[EntityReferenceDTO] = Field(default_factory=list)
    contacts: List[EntityReferenceDTO] = Field(default_factory=list)
    properties: List[EntityReferenceDTO] = Field(default_factory=list)
    opportunities: List[EntityReferenceDTO] = Field(default_factory=list)
    leads: List[EntityReferenceDTO] = Field(default_factory=list)
    documents: List[EntityReferenceDTO] = Field(default_factory=list)
    custom_entities: List[EntityReferenceDTO] = Field(default_factory=list)
    relationships: List[EntityRelationshipResponse] = Field(default_factory=list)
    total_connections: int = 0


class OrganizationResponse(BaseModel):
    """Company-centric Organization Knowledge Graph projection."""
    projection_version: str = "1.0.0"
    company: EntityReferenceDTO
    parent_companies: List[EntityReferenceDTO] = Field(default_factory=list)
    subsidiaries: List[EntityReferenceDTO] = Field(default_factory=list)
    employees: List[EntityReferenceDTO] = Field(default_factory=list)
    decision_makers: List[EntityReferenceDTO] = Field(default_factory=list)
    open_opportunities: List[EntityReferenceDTO] = Field(default_factory=list)
    projects: List[EntityReferenceDTO] = Field(default_factory=list)
    relationships: List[EntityRelationshipResponse] = Field(default_factory=list)
    total_members: int = 0


class PropertyNetworkResponse(BaseModel):
    """Property-centric network projection."""
    projection_version: str = "1.0.0"
    property_entity: EntityReferenceDTO
    owners: List[EntityReferenceDTO] = Field(default_factory=list)
    interested_prospects: List[EntityReferenceDTO] = Field(default_factory=list)
    managing_agents: List[EntityReferenceDTO] = Field(default_factory=list)
    documents: List[EntityReferenceDTO] = Field(default_factory=list)
    relationships: List[EntityRelationshipResponse] = Field(default_factory=list)
    total_connections: int = 0


class OpportunityNetworkResponse(BaseModel):
    """Opportunity-centric deal network projection."""
    projection_version: str = "1.0.0"
    opportunity: EntityReferenceDTO
    buyers: List[EntityReferenceDTO] = Field(default_factory=list)
    sellers: List[EntityReferenceDTO] = Field(default_factory=list)
    decision_makers: List[EntityReferenceDTO] = Field(default_factory=list)
    assigned_agents: List[EntityReferenceDTO] = Field(default_factory=list)
    linked_properties: List[EntityReferenceDTO] = Field(default_factory=list)
    relationships: List[EntityRelationshipResponse] = Field(default_factory=list)
    total_connections: int = 0


class CustomGraphResponse(BaseModel):
    """Generic custom graph projection."""
    projection_version: str = "1.0.0"
    root_entity: Optional[EntityReferenceDTO] = None
    nodes: List[EntityReferenceDTO] = Field(default_factory=list)
    relationships: List[EntityRelationshipResponse] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


# ── Statistics & Export DTOs ──────────────────────────────────────────────────

class GraphStatisticsResponse(BaseModel):
    """Aggregated graph topology, centrality, and health statistics."""
    workspace_id: Optional[uuid.UUID]
    total_nodes: int
    total_relationships: int
    active_relationships: int
    archived_relationships: int
    relationship_type_distribution: Dict[str, int] = Field(default_factory=dict)
    node_type_distribution: Dict[str, int] = Field(default_factory=dict)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    graph_density: float = 0.0
    average_path_length: Optional[float] = None
    relationship_strength_distribution: Dict[str, int] = Field(default_factory=dict)
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    node_centrality_metrics: Dict[str, float] = Field(default_factory=dict)


class VisualizationGraphDTO(BaseModel):
    """Standardized visualization payload compatible with Cytoscape, D3, ReactFlow."""
    format: str = Field("cytoscape", description="Export format (cytoscape, d3, reactflow)")
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "EntityReferenceDTO",
    "RelationshipMetadataDTO",
    "EntityRelationshipCreateRequest",
    "EntityRelationshipUpdateRequest",
    "EntityRelationshipResponse",
    "RelationshipBulkCreateRequest",
    "RelationshipBulkCreateResponse",
    "GraphQueryRequest",
    "GraphTraversalRequest",
    "PathFindingRequest",
    "PathFindingResponse",
    "TreeTraversalRequest",
    "GraphTreeNode",
    "Customer360Response",
    "OrganizationResponse",
    "PropertyNetworkResponse",
    "OpportunityNetworkResponse",
    "CustomGraphResponse",
    "GraphStatisticsResponse",
    "VisualizationGraphDTO",
]
