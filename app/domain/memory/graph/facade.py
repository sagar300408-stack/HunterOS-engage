"""
HunterOS Engage — Knowledge Graph Facade (Phase 2.1.4)

Provides a unified facade exposing both Command and Query services to the Memory domain.
"""

from __future__ import annotations

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
from app.domain.memory.graph.services import GraphCommandService, GraphQueryService
from app.domain.memory.graph.statistics import GraphStatisticsEngine
from app.domain.memory.graph.storage import (
    AbstractGraphStorageProvider,
    SqlAlchemyGraphStorageProvider,
)
from app.domain.memory.graph.traversal.engine import GraphTraversalEngine
from app.domain.memory.graph.traversal.strategies import TraversalResult
from app.domain.memory.graph.validation import (
    RelationshipValidator,
    default_relationship_validator,
)


class KnowledgeGraphFacade:
    """
    Unified entry point for the HunterOS Business Knowledge Graph.
    Delegates to GraphCommandService (mutations) and GraphQueryService (queries).
    """

    def __init__(
        self,
        storage_provider: Optional[AbstractGraphStorageProvider] = None,
        session_factory: Optional[Callable[[], Any]] = None,
        command_service: Optional[GraphCommandService] = None,
        query_service: Optional[GraphQueryService] = None,
        validator: Optional[RelationshipValidator] = None,
        event_publisher: Optional[Callable[[GraphDomainEvent], Any]] = None,
    ) -> None:
        if command_service and query_service:
            self.commands = command_service
            self.queries = query_service
        else:
            storage = storage_provider or SqlAlchemyGraphStorageProvider(session_factory=session_factory)
            write_repo = GraphWriteRepository(storage)
            read_repo = GraphReadRepository(storage)
            valid = validator or default_relationship_validator

            self.commands = GraphCommandService(
                write_repository=write_repo,
                read_repository=read_repo,
                validator=valid,
                event_publisher=event_publisher,
            )
            self.queries = GraphQueryService(
                read_repository=read_repo,
                traversal_engine=GraphTraversalEngine(read_repo),
                projection_engine=GraphProjectionEngine(read_repo),
                statistics_engine=GraphStatisticsEngine(read_repo),
                export_engine=GraphExportEngine(),
            )

    # ── Command Facade Methods ────────────────────────────────────────────────

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
        return await self.commands.create_relationship(
            source=source,
            target=target,
            relationship_type=relationship_type,
            direction=direction,
            strength=strength,
            metadata=metadata,
            workspace_id=workspace_id,
            relationship_id=relationship_id,
            allow_self_loops=allow_self_loops,
            session=session,
        )

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
        return await self.commands.update_relationship(
            relationship_id=relationship_id,
            strength=strength,
            direction=direction,
            metadata_update=metadata_update,
            confidence=confidence,
            last_verified=last_verified,
            updated_by=updated_by,
            session=session,
        )

    async def archive_relationship(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        return await self.commands.archive_relationship(
            relationship_id=relationship_id,
            reason=reason,
            actor=actor,
            session=session,
        )

    async def delete_relationship(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        return await self.commands.delete_relationship(
            relationship_id=relationship_id,
            reason=reason,
            actor=actor,
            session=session,
        )

    async def restore_relationship(
        self,
        relationship_id: uuid.UUID,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        return await self.commands.restore_relationship(
            relationship_id=relationship_id,
            actor=actor,
            session=session,
        )

    async def bulk_create(
        self,
        requests: List[EntityRelationshipCreateRequest],
        workspace_id: Optional[uuid.UUID] = None,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        return await self.commands.bulk_create(
            requests=requests,
            workspace_id=workspace_id,
            session=session,
        )

    # ── Query Facade Methods ──────────────────────────────────────────────────

    async def get_relationship(
        self,
        relationship_id: uuid.UUID,
        session: Any = None,
    ) -> Optional[RelationshipAggregate]:
        return await self.queries.get_by_id(relationship_id, session=session)

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
        return await self.queries.query_relationships(
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            relationship_types=relationship_types,
            statuses=statuses,
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
        return await self.queries.get_direct_relationships(
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
        return await self.queries.traverse_neighbors(
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
        return await self.queries.find_path(
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
        return await self.queries.build_relationship_tree(
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
        return await self.queries.project_customer_360(workspace_id, customer_id, session=session)

    async def project_organization(
        self,
        workspace_id: Optional[uuid.UUID],
        company_id: str | uuid.UUID,
        session: Any = None,
    ) -> OrganizationResponse:
        return await self.queries.project_organization(workspace_id, company_id, session=session)

    async def project_property_network(
        self,
        workspace_id: Optional[uuid.UUID],
        property_id: str | uuid.UUID,
        session: Any = None,
    ) -> PropertyNetworkResponse:
        return await self.queries.project_property_network(workspace_id, property_id, session=session)

    async def project_opportunity_network(
        self,
        workspace_id: Optional[uuid.UUID],
        opportunity_id: str | uuid.UUID,
        session: Any = None,
    ) -> OpportunityNetworkResponse:
        return await self.queries.project_opportunity_network(workspace_id, opportunity_id, session=session)

    async def project_custom(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: GraphNodeType | str,
        entity_id: str,
        max_depth: int = 2,
        session: Any = None,
    ) -> CustomGraphResponse:
        return await self.queries.project_custom(workspace_id, entity_type, entity_id, max_depth=max_depth, session=session)

    async def get_statistics(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> GraphStatisticsResponse:
        return await self.queries.get_statistics(workspace_id, session=session)

    async def export_graph(
        self,
        workspace_id: Optional[uuid.UUID],
        format: str = "cytoscape",
        session: Any = None,
    ) -> VisualizationGraphDTO | List[Dict[str, Any]]:
        return await self.queries.export_graph(workspace_id, format=format, session=session)


__all__ = [
    "KnowledgeGraphFacade",
]
