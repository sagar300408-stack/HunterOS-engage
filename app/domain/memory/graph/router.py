"""
HunterOS Engage — Knowledge Graph REST Router (Phase 2.1.4)

FastAPI endpoints for Knowledge Graph relationships, traversals, projections,
statistics, and visualization schemas under `/api/v1/memory/graph`.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.graph.models import (
    EntityReference,
    GraphDomainError,
    GraphNodeType,
    RelationshipDirection,
    RelationshipMetadata,
    RelationshipNotFoundError,
    RelationshipStatus,
    RelationshipType,
    RelationshipValidationError,
)
from app.domain.memory.graph.schemas import (
    Customer360Response,
    CustomGraphResponse,
    EntityReferenceDTO,
    EntityRelationshipCreateRequest,
    EntityRelationshipResponse,
    EntityRelationshipUpdateRequest,
    GraphQueryRequest,
    GraphStatisticsResponse,
    GraphTraversalRequest,
    GraphTreeNode,
    OpportunityNetworkResponse,
    OrganizationResponse,
    PathFindingRequest,
    PathFindingResponse,
    PropertyNetworkResponse,
    RelationshipBulkCreateRequest,
    RelationshipBulkCreateResponse,
    TreeTraversalRequest,
    VisualizationGraphDTO,
)
from app.domain.memory.graph.storage import SqlAlchemyGraphStorageProvider

router = APIRouter(prefix="/api/v1/memory/graph", tags=["Memory Knowledge Graph"])

# Default singleton facade for router (can be overridden via dependency injection)
_graph_facade: Optional[KnowledgeGraphFacade] = None


def get_graph_facade() -> KnowledgeGraphFacade:
    global _graph_facade
    if _graph_facade is None:
        _graph_facade = KnowledgeGraphFacade()
    return _graph_facade


def set_graph_facade(facade: KnowledgeGraphFacade) -> None:
    global _graph_facade
    _graph_facade = facade


def _to_response_dto(aggregate) -> EntityRelationshipResponse:
    return EntityRelationshipResponse(
        relationship_id=aggregate.id,
        workspace_id=aggregate.workspace_id,
        source=EntityReferenceDTO(
            entity_type=aggregate.source.entity_type,
            entity_id=aggregate.source.entity_id,
            workspace_id=aggregate.source.workspace_id,
            label=aggregate.source.label,
            properties=aggregate.source.properties,
        ),
        target=EntityReferenceDTO(
            entity_type=aggregate.target.entity_type,
            entity_id=aggregate.target.entity_id,
            workspace_id=aggregate.target.workspace_id,
            label=aggregate.target.label,
            properties=aggregate.target.properties,
        ),
        relationship_type=aggregate.relationship_type,
        direction=aggregate.direction,
        strength=aggregate.strength,
        status=aggregate.status,
        metadata=aggregate.metadata.to_dict(),
        version=aggregate.version,
        is_deleted=aggregate.is_deleted,
        created_at=aggregate.created_at,
        updated_at=aggregate.updated_at,
    )


# ── Relationship Lifecycle Endpoints ──────────────────────────────────────────

@router.post(
    "/relationships",
    response_model=EntityRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create graph relationship",
)
async def create_relationship(
    request: EntityRelationshipCreateRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        src = EntityReference.from_dict(request.source.dict())
        tgt = EntityReference.from_dict(request.target.dict())
        meta = RelationshipMetadata.from_dict(request.metadata.dict() if request.metadata else {})
        created = await facade.create_relationship(
            source=src,
            target=tgt,
            relationship_type=request.relationship_type,
            direction=request.direction,
            strength=request.strength,
            metadata=meta,
            workspace_id=request.workspace_id,
        )
        return _to_response_dto(created)
    except RelationshipValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/relationships/bulk",
    response_model=RelationshipBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create graph relationships",
)
async def bulk_create_relationships(
    request: RelationshipBulkCreateRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        created_list = await facade.bulk_create(request.relationships)
        return RelationshipBulkCreateResponse(
            created_count=len(created_list),
            relationship_ids=[r.id for r in created_list],
        )
    except RelationshipValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/relationships/{relationship_id}",
    response_model=EntityRelationshipResponse,
    summary="Get relationship by ID",
)
async def get_relationship(
    relationship_id: uuid.UUID,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    rel = await facade.get_relationship(relationship_id)
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Relationship {relationship_id} not found.")
    return _to_response_dto(rel)


@router.patch(
    "/relationships/{relationship_id}",
    response_model=EntityRelationshipResponse,
    summary="Update relationship",
)
async def update_relationship(
    relationship_id: uuid.UUID,
    request: EntityRelationshipUpdateRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        updated = await facade.update_relationship(
            relationship_id=relationship_id,
            strength=request.strength,
            direction=request.direction,
            metadata_update=request.metadata_update,
            confidence=request.confidence,
            last_verified=request.last_verified,
            updated_by=request.updated_by,
        )
        return _to_response_dto(updated)
    except RelationshipNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Relationship {relationship_id} not found.")
    except GraphDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/relationships/{relationship_id}",
    response_model=EntityRelationshipResponse,
    summary="Soft-delete relationship",
)
async def delete_relationship(
    relationship_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        deleted = await facade.delete_relationship(relationship_id, reason=reason, actor=actor)
        return _to_response_dto(deleted)
    except RelationshipNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Relationship {relationship_id} not found.")


@router.post(
    "/relationships/{relationship_id}/archive",
    response_model=EntityRelationshipResponse,
    summary="Archive relationship",
)
async def archive_relationship(
    relationship_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        archived = await facade.archive_relationship(relationship_id, reason=reason, actor=actor)
        return _to_response_dto(archived)
    except RelationshipNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Relationship {relationship_id} not found.")


@router.post(
    "/relationships/{relationship_id}/restore",
    response_model=EntityRelationshipResponse,
    summary="Restore relationship",
)
async def restore_relationship(
    relationship_id: uuid.UUID,
    actor: Optional[str] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    try:
        restored = await facade.restore_relationship(relationship_id, actor=actor)
        return _to_response_dto(restored)
    except RelationshipNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Relationship {relationship_id} not found.")


# ── Query & Traversal Endpoints ───────────────────────────────────────────────

@router.post(
    "/query",
    response_model=List[EntityRelationshipResponse],
    summary="Query relationships with filters",
)
async def query_relationships(
    request: GraphQueryRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    results = await facade.query_relationships(
        workspace_id=request.workspace_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        relationship_types=request.relationship_types,
        statuses=request.statuses,
        min_strength=request.min_strength,
        min_confidence=request.min_confidence,
        limit=request.limit,
        offset=request.offset,
    )
    return [_to_response_dto(r) for r in results]


@router.get(
    "/direct",
    response_model=List[EntityRelationshipResponse],
    summary="Get 1-hop direct relationships for an entity",
)
async def get_direct_relationships(
    entity_type: GraphNodeType = Query(...),
    entity_id: str = Query(...),
    workspace_id: Optional[uuid.UUID] = Query(None),
    direction: str = Query("ALL"),
    min_strength: float = Query(0.0),
    min_confidence: float = Query(0.0),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    results = await facade.get_direct_relationships(
        workspace_id=workspace_id,
        entity_type=entity_type,
        entity_id=entity_id,
        direction=direction,
        min_strength=min_strength,
        min_confidence=min_confidence,
    )
    return [_to_response_dto(r) for r in results]


@router.post(
    "/traverse/neighbors",
    summary="Multi-hop neighborhood traversal",
)
async def traverse_neighbors(
    request: GraphTraversalRequest,
    strategy: str = Query("bfs"),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    res = await facade.traverse_neighbors(
        workspace_id=request.workspace_id,
        start_entity_type=request.start_entity_type,
        start_entity_id=request.start_entity_id,
        max_depth=request.max_depth,
        strategy_name=strategy,
        relationship_types=request.relationship_types,
        direction=request.direction.value,
        min_strength=request.min_strength,
        min_confidence=request.min_confidence,
        limit=request.limit,
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
    edge_dtos = [_to_response_dto(e) for e in res.edges]
    return {
        "nodes": node_dtos,
        "edges": edge_dtos,
        "depths": res.depths,
        "total_nodes": len(node_dtos),
        "total_edges": len(edge_dtos),
    }


@router.post(
    "/traverse/path",
    response_model=PathFindingResponse,
    summary="Shortest / weighted path finding between two entities",
)
async def find_path(
    request: PathFindingRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.find_path(
        workspace_id=request.workspace_id,
        source_entity_type=request.source_entity_type,
        source_entity_id=request.source_entity_id,
        target_entity_type=request.target_entity_type,
        target_entity_id=request.target_entity_id,
        max_depth=request.max_depth,
        weighted=request.weighted,
        min_confidence=request.min_confidence,
    )


@router.post(
    "/traverse/tree",
    response_model=GraphTreeNode,
    summary="Generate hierarchical tree rooted at an entity",
)
async def build_tree(
    request: TreeTraversalRequest,
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.build_relationship_tree(
        workspace_id=request.workspace_id,
        root_entity_type=request.root_entity_type,
        root_entity_id=request.root_entity_id,
        max_depth=request.max_depth,
        relationship_types=request.relationship_types,
        direction=request.direction.value,
    )


# ── Projection Endpoints ──────────────────────────────────────────────────────

@router.get(
    "/projections/customer-360/{customer_id}",
    response_model=Customer360Response,
    summary="Customer 360 Knowledge Graph projection",
)
async def get_customer_360_projection(
    customer_id: str,
    workspace_id: Optional[uuid.UUID] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.project_customer_360(workspace_id=workspace_id, customer_id=customer_id)


@router.get(
    "/projections/organization/{company_id}",
    response_model=OrganizationResponse,
    summary="Organization Knowledge Graph projection",
)
async def get_organization_projection(
    company_id: str,
    workspace_id: Optional[uuid.UUID] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.project_organization(workspace_id=workspace_id, company_id=company_id)


@router.get(
    "/projections/property-network/{property_id}",
    response_model=PropertyNetworkResponse,
    summary="Property Network Knowledge Graph projection",
)
async def get_property_network_projection(
    property_id: str,
    workspace_id: Optional[uuid.UUID] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.project_property_network(workspace_id=workspace_id, property_id=property_id)


@router.get(
    "/projections/opportunity-network/{opportunity_id}",
    response_model=OpportunityNetworkResponse,
    summary="Opportunity Deal Network Knowledge Graph projection",
)
async def get_opportunity_network_projection(
    opportunity_id: str,
    workspace_id: Optional[uuid.UUID] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.project_opportunity_network(workspace_id=workspace_id, opportunity_id=opportunity_id)


# ── Statistics & Export Endpoints ─────────────────────────────────────────────

@router.get(
    "/statistics",
    response_model=GraphStatisticsResponse,
    summary="Get Knowledge Graph statistics and topology metrics",
)
async def get_graph_statistics(
    workspace_id: Optional[uuid.UUID] = Query(None),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.get_statistics(workspace_id=workspace_id)


@router.get(
    "/export",
    summary="Export Knowledge Graph for visualization (Cytoscape, D3, ReactFlow, Tabular)",
)
async def export_graph(
    workspace_id: Optional[uuid.UUID] = Query(None),
    format: str = Query("cytoscape"),
    facade: KnowledgeGraphFacade = Depends(get_graph_facade),
):
    return await facade.export_graph(workspace_id=workspace_id, format=format)


__all__ = [
    "router",
    "get_graph_facade",
    "set_graph_facade",
]
