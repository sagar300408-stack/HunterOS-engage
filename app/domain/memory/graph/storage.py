"""
HunterOS Engage — Graph Storage Provider Abstraction (Phase 2.1.4)

Decouples Graph operations from the underlying database.
Today: SQLAlchemy (PostgreSQL / SQLite).
Future: Neo4j, Amazon Neptune, Azure Cosmos Graph, JanusGraph.
"""

from __future__ import annotations

import abc
import uuid
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.memory.graph.models import (
    EntityReference,
    EntityRelationship,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipStatus,
    RelationshipType,
)


class AbstractGraphStorageProvider(abc.ABC):
    """
    Abstract interface for Knowledge Graph persistence.
    Provides vendor-agnostic graph CRUD and relationship querying.
    """

    @abc.abstractmethod
    async def save_relationship(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Persist a new relationship aggregate."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_relationship_by_id(
        self,
        relationship_id: uuid.UUID,
        session: Any = None,
    ) -> Optional[RelationshipAggregate]:
        """Retrieve relationship aggregate by unique UUID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update_relationship(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        """Update an existing relationship aggregate."""
        raise NotImplementedError

    @abc.abstractmethod
    async def query_relationships(
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
        """Query relationships matching multi-criteria filters."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_incident_edges(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: str,
        direction: str = "ALL",
        include_deleted: bool = False,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Fetch all 1-hop incident edges for a node."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all_active_edges_for_workspace(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        """Retrieve all active relationships for a workspace (useful for traversals/analytics)."""
        raise NotImplementedError


class SqlAlchemyGraphStorageProvider(AbstractGraphStorageProvider):
    """
    SQLAlchemy implementation of GraphStorageProvider supporting AsyncSession and sync Session.
    """

    def __init__(self, session_factory: Optional[Callable[[], Any]] = None) -> None:
        self._session_factory = session_factory

    def _resolve_session(self, explicit_session: Any = None) -> Any:
        if explicit_session is not None:
            return explicit_session
        if self._session_factory is not None:
            return self._session_factory()
        raise RuntimeError("No database session provided to SqlAlchemyGraphStorageProvider.")

    async def save_relationship(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        sess = self._resolve_session(session)
        rel_type_str = aggregate.relationship_type.value if hasattr(aggregate.relationship_type, "value") else str(aggregate.relationship_type)
        dir_str = aggregate.direction.value if hasattr(aggregate.direction, "value") else str(aggregate.direction)
        status_str = aggregate.status.value if hasattr(aggregate.status, "value") else str(aggregate.status)
        src_type_str = aggregate.source.entity_type.value if hasattr(aggregate.source.entity_type, "value") else str(aggregate.source.entity_type)
        tgt_type_str = aggregate.target.entity_type.value if hasattr(aggregate.target.entity_type, "value") else str(aggregate.target.entity_type)

        meta_payload = {
            "source_properties": aggregate.source.properties,
            "target_properties": aggregate.target.properties,
            "extra": aggregate.metadata.extra,
        }

        entity = EntityRelationship(
            id=aggregate.id,
            workspace_id=aggregate.workspace_id,
            relationship_type=rel_type_str,
            source_node_type=src_type_str,
            source_node_id=str(aggregate.source.entity_id),
            source_label=aggregate.source.label,
            target_node_type=tgt_type_str,
            target_node_id=str(aggregate.target.entity_id),
            target_label=aggregate.target.label,
            direction=dir_str,
            strength=aggregate.strength,
            status=status_str,
            is_deleted=aggregate.is_deleted,
            confidence=aggregate.metadata.confidence,
            source=aggregate.metadata.source,
            created_by=aggregate.metadata.created_by,
            last_verified=aggregate.metadata.last_verified,
            version=aggregate.version,
            metadata_payload=meta_payload,
            created_at=aggregate.created_at,
            updated_at=aggregate.updated_at,
        )

        if isinstance(sess, AsyncSession):
            sess.add(entity)
            await sess.flush()
        else:
            sess.add(entity)
            sess.flush()

        return aggregate

    async def get_relationship_by_id(
        self,
        relationship_id: uuid.UUID,
        session: Any = None,
    ) -> Optional[RelationshipAggregate]:
        sess = self._resolve_session(session)
        stmt = select(EntityRelationship).where(EntityRelationship.id == relationship_id)

        if isinstance(sess, AsyncSession):
            result = await sess.execute(stmt)
            entity = result.scalars().first()
        else:
            entity = sess.execute(stmt).scalars().first()

        if not entity:
            return None
        return entity.to_aggregate()

    async def update_relationship(
        self,
        aggregate: RelationshipAggregate,
        session: Any = None,
    ) -> RelationshipAggregate:
        sess = self._resolve_session(session)
        dir_str = aggregate.direction.value if hasattr(aggregate.direction, "value") else str(aggregate.direction)
        status_str = aggregate.status.value if hasattr(aggregate.status, "value") else str(aggregate.status)

        meta_payload = {
            "source_properties": aggregate.source.properties,
            "target_properties": aggregate.target.properties,
            "extra": aggregate.metadata.extra,
        }

        stmt = (
            update(EntityRelationship)
            .where(EntityRelationship.id == aggregate.id)
            .values(
                direction=dir_str,
                strength=aggregate.strength,
                status=status_str,
                is_deleted=aggregate.is_deleted,
                confidence=aggregate.metadata.confidence,
                source=aggregate.metadata.source,
                last_verified=aggregate.metadata.last_verified,
                version=aggregate.version,
                metadata_payload=meta_payload,
                updated_at=aggregate.updated_at,
            )
        )

        if isinstance(sess, AsyncSession):
            await sess.execute(stmt)
            await sess.flush()
        else:
            sess.execute(stmt)
            sess.flush()

        return aggregate

    async def query_relationships(
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
        sess = self._resolve_session(session)
        filters = []

        if workspace_id is not None:
            filters.append(EntityRelationship.workspace_id == workspace_id)

        if not include_deleted:
            filters.append(EntityRelationship.is_deleted == False)

        if entity_type and entity_id:
            filters.append(
                or_(
                    and_(
                        EntityRelationship.source_node_type == entity_type,
                        EntityRelationship.source_node_id == entity_id,
                    ),
                    and_(
                        EntityRelationship.target_node_type == entity_type,
                        EntityRelationship.target_node_id == entity_id,
                    ),
                )
            )
        elif entity_type:
            filters.append(
                or_(
                    EntityRelationship.source_node_type == entity_type,
                    EntityRelationship.target_node_type == entity_type,
                )
            )
        elif entity_id:
            filters.append(
                or_(
                    EntityRelationship.source_node_id == entity_id,
                    EntityRelationship.target_node_id == entity_id,
                )
            )

        if relationship_types:
            filters.append(EntityRelationship.relationship_type.in_(relationship_types))

        if statuses:
            filters.append(EntityRelationship.status.in_(statuses))

        if min_strength is not None:
            filters.append(EntityRelationship.strength >= min_strength)

        if min_confidence is not None:
            filters.append(EntityRelationship.confidence >= min_confidence)

        stmt = (
            select(EntityRelationship)
            .where(and_(*filters))
            .order_by(EntityRelationship.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if isinstance(sess, AsyncSession):
            result = await sess.execute(stmt)
            entities = result.scalars().all()
        else:
            entities = sess.execute(stmt).scalars().all()

        return [e.to_aggregate() for e in entities]

    async def get_incident_edges(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: str,
        direction: str = "ALL",
        include_deleted: bool = False,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        sess = self._resolve_session(session)
        filters = []
        if workspace_id is not None:
            filters.append(EntityRelationship.workspace_id == workspace_id)
        if not include_deleted:
            filters.append(EntityRelationship.is_deleted == False)
            filters.append(EntityRelationship.status == RelationshipStatus.ACTIVE.value)

        dir_upper = direction.upper()
        if dir_upper == "OUTGOING":
            filters.append(
                and_(
                    EntityRelationship.source_node_type == entity_type,
                    EntityRelationship.source_node_id == entity_id,
                )
            )
        elif dir_upper == "INCOMING":
            filters.append(
                and_(
                    EntityRelationship.target_node_type == entity_type,
                    EntityRelationship.target_node_id == entity_id,
                )
            )
        else:
            filters.append(
                or_(
                    and_(
                        EntityRelationship.source_node_type == entity_type,
                        EntityRelationship.source_node_id == entity_id,
                    ),
                    and_(
                        EntityRelationship.target_node_type == entity_type,
                        EntityRelationship.target_node_id == entity_id,
                    ),
                )
            )

        stmt = select(EntityRelationship).where(and_(*filters)).order_by(EntityRelationship.created_at.desc())

        if isinstance(sess, AsyncSession):
            result = await sess.execute(stmt)
            entities = result.scalars().all()
        else:
            entities = sess.execute(stmt).scalars().all()

        return [e.to_aggregate() for e in entities]

    async def get_all_active_edges_for_workspace(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        sess = self._resolve_session(session)
        filters = [
            EntityRelationship.is_deleted == False,
            EntityRelationship.status == RelationshipStatus.ACTIVE.value,
        ]
        if workspace_id is not None:
            filters.append(EntityRelationship.workspace_id == workspace_id)

        stmt = select(EntityRelationship).where(and_(*filters))

        if isinstance(sess, AsyncSession):
            result = await sess.execute(stmt)
            entities = result.scalars().all()
        else:
            entities = sess.execute(stmt).scalars().all()

        return [e.to_aggregate() for e in entities]


__all__ = [
    "AbstractGraphStorageProvider",
    "SqlAlchemyGraphStorageProvider",
]
