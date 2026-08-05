"""
HunterOS Engage — Knowledge Graph CQRS Services (Phase 2.1.4)

Implements:
  - GraphCommandService: Handles all write operations, aggregate consistency, validations, and domain event publishing.
  - GraphQueryService: Handles read-only queries, traversals, projections, statistics, and visualization exports.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.domain.memory.graph.export import GraphExportEngine
from app.domain.memory.graph.models import (
    EntityReference,
    GraphDomainEvent,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipMetadata,
    RelationshipNotFoundError,
    RelationshipStatus,
    RelationshipType,
)
from app.domain.memory.graph.node_registry import NodeRegistry, default_node_registry
from app.domain.memory.graph.projections.engine import GraphProjectionEngine
from app.domain.memory.graph.repository import GraphReadRepository, GraphWriteRepository
from app.domain.memory.graph.schemas import (
    Customer360Response,
    CustomGraphResponse,
    EntityRelationshipCreateRequest,
    GraphStatisticsResponse,
    GraphTreeNode,
    OpportunityNetworkResponse,
    OrganizationResponse,
    PathFindingResponse,
    PropertyNetworkResponse,
    VisualizationGraphDTO,
)
from app.domain.memory.graph.statistics import GraphStatisticsEngine
from app.domain.memory.graph.traversal.engine import GraphTraversalEngine
from app.domain.memory.graph.traversal.strategies import TraversalResult
from app.domain.memory.graph.validation import (
    RelationshipValidator,
    default_relationship_validator,
)

logger = logging.getLogger(__name__)


class GraphCommandService:
    """
    CQRS Command Service for mutating Knowledge Graph relationships.
    Orchestrates validation, aggregate boundaries, persistence, and domain event emission.
    """

    def __init__(
        self,
        write_repository: GraphWriteRepository,
        read_repository: GraphReadRepository,
        validator: Optional[RelationshipValidator] = None,
        event_publisher: Optional[Callable[[GraphDomainEvent], Any]] = None,
    ) -> None:
        self._write_repo = write_repository
        self._read_repo = read_repository
        self._validator = validator or default_relationship_validator
        self._event_publisher = event_publisher
        self._published_events: List[GraphDomainEvent] = []

    def get_published_events(self) -> List[GraphDomainEvent]:
        """Inspection helper for test suites."""
        return list(self._published_events)

    async def _publish_events(self, events: List[GraphDomainEvent]) -> None:
        for event in events:
            self._published_events.append(event)
            if self._event_publisher:
                try:
                    res = self._event_publisher(event)
                    if hasattr(res, "__await__"):
                        await res
                except Exception as exc:
                    logger.warning(f"Error publishing graph domain event {event}: {exc}")

    async def create_relationship(
        self,
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        direction: RelationshipDirection = RelationshipDirection.DIRECTED,
        strength: float = 1.0,
        metadata: Optional[RelationshipMetadata] = None,
        workspace_id: Optional[uuid.UUID] = None,
        relationship_id: Optional[uuid.UUID] = None,
        allow_self_loops: bool = False,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Create and persist a new validated relationship aggregate."""
        ws_id = workspace_id or source.workspace_id or target.workspace_id

        # Fetch existing active edges in workspace for validation checks
        existing_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=ws_id,
            session=session,
        )
        existing_dicts = [
            {
                "source_key": e.source.key,
                "target_key": e.target.key,
                "relationship_type": e.relationship_type.value if hasattr(e.relationship_type, "value") else str(e.relationship_type),
                "is_deleted": e.is_deleted,
                "status": e.status.value if hasattr(e.status, "value") else str(e.status),
            }
            for e in existing_edges
        ]

        # Validate
        self._validator.validate_relationship(
            source=source,
            target=target,
            relationship_type=relationship_type,
            workspace_id=ws_id,
            existing_edges=existing_dicts,
            allow_self_loops=allow_self_loops,
        )

        aggregate = RelationshipAggregate.create(
            workspace_id=ws_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            direction=direction,
            strength=strength,
            metadata=metadata,
            relationship_id=relationship_id,
        )

        saved = await self._write_repo.save(aggregate, session=session)
        events = aggregate.collect_events()
        await self._publish_events(events)

        return saved

    async def update_relationship(
        self,
        relationship_id: uuid.UUID,
        strength: Optional[float] = None,
        direction: Optional[RelationshipDirection] = None,
        metadata_update: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        last_verified: Optional[Any] = None,
        updated_by: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Update an existing relationship aggregate."""
        agg = await self._read_repo.get_by_id(relationship_id, session=session)
        if not agg:
            raise RelationshipNotFoundError(f"Relationship {relationship_id} not found.")

        agg.update(
            strength=strength,
            direction=direction,
            metadata_update=metadata_update,
            confidence=confidence,
            last_verified=last_verified,
            updated_by=updated_by,
        )

        updated = await self._write_repo.update(agg, session=session)
        events = agg.collect_events()
        await self._publish_events(events)

        return updated

    async def archive_relationship(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Archive a relationship."""
        archived = await self._write_repo.archive(
            relationship_id=relationship_id,
            reason=reason,
            actor=actor,
            session=session,
        )
        events = archived.collect_events()
        await self._publish_events(events)
        return archived

    async def delete_relationship(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Soft-delete a relationship."""
        deleted = await self._write_repo.delete(
            relationship_id=relationship_id,
            reason=reason,
            actor=actor,
            session=session,
        )
        events = deleted.collect_events()
        await self._publish_events(events)
        return deleted

    async def restore_relationship(
        self,
        relationship_id: uuid.UUID,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Restore a soft-deleted/archived relationship."""
        restored = await self._write_repo.restore(
            relationship_id=relationship_id,
            actor=actor,
            session=session,
        )
        events = restored.collect_events()
        await self._publish_events(events)
        return restored

    async def bulk_create(
        self,
        requests: List[EntityRelationshipCreateRequest],
        workspace_id: Optional[uuid.UUID] = None,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Batch create multiple relationships."""
        results = []
        for req in requests:
            ws = req.workspace_id or workspace_id
            src = EntityReference.from_dict(req.source.dict())
            tgt = EntityReference.from_dict(req.target.dict())
            meta = RelationshipMetadata.from_dict(req.metadata.dict() if req.metadata else {})
            created = await self.create_relationship(
                source=src,
                target=tgt,
                relationship_type=req.relationship_type,
                direction=req.direction,
                strength=req.strength,
                metadata=meta,
                workspace_id=ws,
                session=session,
            )
            results.append(created)
        return results


class GraphQueryService:
    """
    CQRS Query Service for retrieving Knowledge Graph data, executing traversals,
    generating projections, computing metrics, and exporting visualization schemas.
    """

    def __init__(
        self,
        read_repository: GraphReadRepository,
        traversal_engine: Optional[GraphTraversalEngine] = None,
        projection_engine: Optional[GraphProjectionEngine] = None,
        statistics_engine: Optional[GraphStatisticsEngine] = None,
        export_engine: Optional[GraphExportEngine] = None,
    ) -> None:
        self._read_repo = read_repository
        self._traversal = traversal_engine or GraphTraversalEngine(read_repository)
        self._projections = projection_engine or GraphProjectionEngine(read_repository)
        self._statistics = statistics_engine or GraphStatisticsEngine(read_repository)
        self._export = export_engine or GraphExportEngine()

    async def get_by_id(
        self,
        relationship_id: uuid.UUID,
        session: Any = None,
    ) -> Optional[RelationshipAggregate]:
        return await self._read_repo.get_by_id(relationship_id, session=session)

    async def query_relationships(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        entity_type: Optional[GraphNodeType | str] = None,
        entity_id: Optional[str] = None,
        relationship_types: Optional[List[RelationshipType | str]] = None,
        statuses: Optional[List[RelationshipStatus | str]] = None,
        min_strength: Optional[float] = None,
        min_confidence: Optional[float] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        t_str = entity_type.value if hasattr(entity_type, "value") else str(entity_type) if entity_type else None
        rel_types = [t.value if hasattr(t, "value") else str(t) for t in relationship_types] if relationship_types else None
        st_list = [s.value if hasattr(s, "value") else str(s) for s in statuses] if statuses else None

        return await self._read_repo.query(
            workspace_id=workspace_id,
            entity_type=t_str,
            entity_id=entity_id,
            relationship_types=rel_types,
            statuses=st_list,
            min_strength=min_strength,
            min_confidence=min_confidence,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
            session=session,
        )

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
        return await self._traversal.get_direct_relationships(
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            direction=direction,
            relationship_types=relationship_types,
            min_strength=min_strength,
            min_confidence=min_confidence,
            session=session,
        )

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
        return await self._traversal.traverse_neighbors(
            workspace_id=workspace_id,
            start_entity_type=start_entity_type,
            start_entity_id=start_entity_id,
            max_depth=max_depth,
            strategy_name=strategy_name,
            relationship_types=relationship_types,
            direction=direction,
            min_strength=min_strength,
            min_confidence=min_confidence,
            limit=limit,
            session=session,
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
        return await self._traversal.find_path(
            workspace_id=workspace_id,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            max_depth=max_depth,
            weighted=weighted,
            min_confidence=min_confidence,
            session=session,
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
        return await self._traversal.build_relationship_tree(
            workspace_id=workspace_id,
            root_entity_type=root_entity_type,
            root_entity_id=root_entity_id,
            max_depth=max_depth,
            relationship_types=relationship_types,
            direction=direction,
            session=session,
        )

    async def project_customer_360(
        self,
        workspace_id: Optional[uuid.UUID],
        customer_id: str | uuid.UUID,
        session: Any = None,
    ) -> Customer360Response:
        return await self._projections.project_customer_360(workspace_id, customer_id, session=session)

    async def project_organization(
        self,
        workspace_id: Optional[uuid.UUID],
        company_id: str | uuid.UUID,
        session: Any = None,
    ) -> OrganizationResponse:
        return await self._projections.project_organization(workspace_id, company_id, session=session)

    async def project_property_network(
        self,
        workspace_id: Optional[uuid.UUID],
        property_id: str | uuid.UUID,
        session: Any = None,
    ) -> PropertyNetworkResponse:
        return await self._projections.project_property_network(workspace_id, property_id, session=session)

    async def project_opportunity_network(
        self,
        workspace_id: Optional[uuid.UUID],
        opportunity_id: str | uuid.UUID,
        session: Any = None,
    ) -> OpportunityNetworkResponse:
        return await self._projections.project_opportunity_network(workspace_id, opportunity_id, session=session)

    async def project_custom(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: GraphNodeType | str,
        entity_id: str,
        max_depth: int = 2,
        session: Any = None,
    ) -> CustomGraphResponse:
        return await self._projections.project_custom(workspace_id, entity_type, entity_id, max_depth=max_depth, session=session)

    async def get_statistics(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> GraphStatisticsResponse:
        return await self._statistics.compute_statistics(workspace_id, session=session)

    async def export_graph(
        self,
        workspace_id: Optional[uuid.UUID],
        format: str = "cytoscape",
        session: Any = None,
    ) -> VisualizationGraphDTO | List[Dict[str, Any]]:
        edges = await self._read_repo.get_all_active_edges_for_workspace(workspace_id=workspace_id, session=session)
        fmt = format.lower()
        if fmt == "cytoscape":
            return self._export.export_cytoscape(edges)
        elif fmt == "d3":
            return self._export.export_d3(edges)
        elif fmt == "reactflow":
            return self._export.export_reactflow(edges)
        elif fmt == "tabular":
            return self._export.export_tabular(edges)
        return self._export.export_cytoscape(edges)


__all__ = [
    "GraphCommandService",
    "GraphQueryService",
]
