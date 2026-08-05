"""
HunterOS Engage — Knowledge Graph CQRS Repositories (Phase 2.1.4)

Separates graph persistence into dedicated Write and Read repositories:
  - GraphWriteRepository: Mutations, state transitions, aggregate consistency.
  - GraphReadRepository: Read-only queries, incident lookups, graph traversals.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.domain.memory.graph.models import (
    GraphNodeType,
    RelationshipAggregate,
    RelationshipNotFoundError,
    RelationshipStatus,
    RelationshipType,
)
from app.domain.memory.graph.storage import (
    AbstractGraphStorageProvider,
    SqlAlchemyGraphStorageProvider,
)


class GraphWriteRepository:
    """
    Write-side repository for Knowledge Graph aggregates.
    Handles persistence of mutations, status updates, and lifecycle operations.
    """

    def __init__(self, storage_provider: AbstractGraphStorageProvider) -> None:
        self._storage = storage_provider

    async def save(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Persist a new relationship aggregate."""
        return await self._storage.save_relationship(aggregate, session=session)

    async def update(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Persist changes to an existing relationship aggregate."""
        return await self._storage.update_relationship(aggregate, session=session)

    async def archive(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Transition relationship to ARCHIVED status."""
        agg = await self._storage.get_relationship_by_id(relationship_id, session=session)
        if not agg:
            raise RelationshipNotFoundError(f"Relationship {relationship_id} not found.")
        agg.archive(reason=reason, actor=actor)
        return await self._storage.update_relationship(agg, session=session)

    async def delete(
        self,
        relationship_id: uuid.UUID,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Soft-delete relationship."""
        agg = await self._storage.get_relationship_by_id(relationship_id, session=session)
        if not agg:
            raise RelationshipNotFoundError(f"Relationship {relationship_id} not found.")
        agg.delete(reason=reason, actor=actor)
        return await self._storage.update_relationship(agg, session=session)

    async def restore(
        self,
        relationship_id: uuid.UUID,
        actor: Optional[str] = None,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Restore soft-deleted or archived relationship back to ACTIVE."""
        agg = await self._storage.get_relationship_by_id(relationship_id, session=session)
        if not agg:
            raise RelationshipNotFoundError(f"Relationship {relationship_id} not found.")
        agg.restore(actor=actor)
        return await self._storage.update_relationship(agg, session=session)


class GraphReadRepository:
    """
    Read-side repository for Knowledge Graph queries.
    Provides fast, immutable data retrieval for traversals, projections, and analytics.
    """

    def __init__(self, storage_provider: AbstractGraphStorageProvider) -> None:
        self._storage = storage_provider

    async def get_by_id(
        self,
        relationship_id: uuid.UUID,
        session: Any = None,
    ) -> Optional[RelationshipAggregate]:
        """Fetch relationship by ID."""
        return await self._storage.get_relationship_by_id(relationship_id, session=session)

    async def query(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        relationship_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        min_strength: Optional[float] = None,
        min_confidence: Optional[float] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Query relationships with multi-criteria filtering."""
        return await self._storage.query_relationships(
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

    async def get_incident_edges(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: str,
        direction: str = "ALL",
        include_deleted: bool = False,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Fetch 1-hop incident edges for a node."""
        return await self._storage.get_incident_edges(
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            direction=direction,
            include_deleted=include_deleted,
            session=session,
        )

    async def get_all_active_edges_for_workspace(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Fetch all active edges in a workspace."""
        return await self._storage.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )


__all__ = [
    "GraphWriteRepository",
    "GraphReadRepository",
]
