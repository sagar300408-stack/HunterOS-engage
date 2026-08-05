"""
HunterOS Engage — Knowledge Graph Domain Models, Aggregate & Domain Events (Phase 2.1.4)

Provides the domain entity definitions, aggregate root, value objects, and domain events
for the HunterOS Business Knowledge Graph.
"""

from __future__ import annotations

import copy
import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles

from app.domain.conversations.models import Base


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class GraphDomainError(ValueError):
    """Base domain exception for knowledge graph errors."""
    pass


class RelationshipValidationError(GraphDomainError):
    """Raised when a relationship fails structural or domain validation."""
    pass


class DuplicateRelationshipError(RelationshipValidationError):
    """Raised when an identical active relationship already exists."""
    pass


class CircularRelationshipError(RelationshipValidationError):
    """Raised when a circular reference is detected on a hierarchical relationship."""
    pass


class IncompatibleNodeTypesError(RelationshipValidationError):
    """Raised when source and target node types are incompatible with the relationship type."""
    pass


class RelationshipNotFoundError(GraphDomainError):
    """Raised when a requested relationship does not exist."""
    pass


class CrossWorkspaceRelationshipError(RelationshipValidationError):
    """Raised when entities belonging to different workspaces are linked."""
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────

class GraphNodeType(str, enum.Enum):
    """Supported graph node entity types."""
    CUSTOMER = "CUSTOMER"
    COMPANY = "COMPANY"
    CONTACT = "CONTACT"
    PROPERTY = "PROPERTY"
    OPPORTUNITY = "OPPORTUNITY"
    LEAD = "LEAD"
    EMPLOYEE = "EMPLOYEE"
    PROJECT = "PROJECT"
    DOCUMENT = "DOCUMENT"
    CUSTOM = "CUSTOM"


class RelationshipType(str, enum.Enum):
    """Supported business relationship edge types."""
    KNOWS = "KNOWS"
    WORKS_FOR = "WORKS_FOR"
    DECISION_MAKER_FOR = "DECISION_MAKER_FOR"
    INTERESTED_IN = "INTERESTED_IN"
    OWNS = "OWNS"
    MANAGES = "MANAGES"
    REFERRED_BY = "REFERRED_BY"
    RELATED_TO = "RELATED_TO"
    MEMBER_OF = "MEMBER_OF"
    CREATED = "CREATED"
    ASSIGNED_TO = "ASSIGNED_TO"
    CUSTOM = "CUSTOM"


class RelationshipDirection(str, enum.Enum):
    """Directional semantics of graph edges."""
    DIRECTED = "DIRECTED"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    UNDIRECTED = "UNDIRECTED"


class RelationshipStatus(str, enum.Enum):
    """Lifecycle status of a relationship."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"


# ── Value Objects ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EntityReference:
    """
    Immutable reference pointer to an existing business entity in HunterOS.
    The graph stores references to business entities rather than duplicating their data.
    """
    entity_type: GraphNodeType
    entity_id: str
    workspace_id: Optional[uuid.UUID] = None
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.entity_type.value if hasattr(self.entity_type, 'value') else self.entity_type}:{self.entity_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type),
            "entity_id": str(self.entity_id),
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "label": self.label,
            "properties": dict(self.properties),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityReference":
        raw_type = data.get("entity_type", "CUSTOM")
        try:
            node_type = GraphNodeType(raw_type)
        except ValueError:
            node_type = GraphNodeType.CUSTOM

        ws_id = data.get("workspace_id")
        if ws_id and isinstance(ws_id, str):
            try:
                ws_id = uuid.UUID(ws_id)
            except ValueError:
                pass

        return cls(
            entity_type=node_type,
            entity_id=str(data.get("entity_id", "")),
            workspace_id=ws_id,
            label=data.get("label"),
            properties=dict(data.get("properties") or {}),
        )


@dataclass(frozen=True)
class RelationshipMetadata:
    """
    Provenance and confidence metadata for graph relationships.
    Tracks confidence (e.g. 1.0 for CRM import, 0.72 for CI extraction), source, and verification.
    """
    confidence: float = 1.0
    source: str = "manual_entry"
    created_by: Optional[str] = None
    last_verified: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def custom_attributes(self) -> Dict[str, Any]:
        return self.extra

    @custom_attributes.setter
    def custom_attributes(self, val: Dict[str, Any]) -> None:
        self.extra = val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "source": self.source,
            "created_by": self.created_by,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipMetadata":
        lv = data.get("last_verified")
        if isinstance(lv, str):
            try:
                lv = datetime.fromisoformat(lv)
            except Exception:
                lv = None
        return cls(
            confidence=float(data.get("confidence", 1.0)),
            source=str(data.get("source", "manual_entry")),
            created_by=data.get("created_by"),
            last_verified=lv,
            extra=dict(data.get("extra") or {}),
        )


# ── Domain Events ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GraphDomainEvent:
    """Base class for knowledge graph domain events."""
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RelationshipCreatedEvent(GraphDomainEvent):
    relationship_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[uuid.UUID] = None
    relationship_type: str = ""
    source_key: str = ""
    target_key: str = ""
    strength: float = 1.0
    confidence: float = 1.0
    created_by: Optional[str] = None


@dataclass(frozen=True)
class RelationshipUpdatedEvent(GraphDomainEvent):
    relationship_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[uuid.UUID] = None
    relationship_type: str = ""
    strength: float = 1.0
    confidence: float = 1.0
    status: str = "ACTIVE"
    version: int = 1
    updated_by: Optional[str] = None


@dataclass(frozen=True)
class RelationshipArchivedEvent(GraphDomainEvent):
    relationship_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    actor: Optional[str] = None


@dataclass(frozen=True)
class RelationshipDeletedEvent(GraphDomainEvent):
    relationship_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    actor: Optional[str] = None


@dataclass(frozen=True)
class RelationshipRestoredEvent(GraphDomainEvent):
    relationship_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[uuid.UUID] = None
    actor: Optional[str] = None


# ── Domain Aggregate: RelationshipAggregate ──────────────────────────────────

class RelationshipAggregate:
    """
    Domain Aggregate for Knowledge Graph relationships.
    Owns consistency, state transitions, version incrementing, metadata evolution,
    and domain event publication.
    """

    def __init__(
        self,
        id: uuid.UUID,
        workspace_id: Optional[uuid.UUID],
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        direction: RelationshipDirection = RelationshipDirection.DIRECTED,
        strength: float = 1.0,
        status: RelationshipStatus = RelationshipStatus.ACTIVE,
        metadata: Optional[RelationshipMetadata] = None,
        version: int = 1,
        is_deleted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.workspace_id = workspace_id
        self.source = source
        self.target = target
        self.relationship_type = relationship_type
        self.direction = direction
        self.strength = max(0.0, min(1.0, float(strength)))
        self.status = status
        self.metadata = metadata or RelationshipMetadata()
        self.version = max(1, int(version))
        self.is_deleted = is_deleted
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

        self._domain_events: List[GraphDomainEvent] = []

    @property
    def events(self) -> List[GraphDomainEvent]:
        """Access uncommitted domain events."""
        return list(self._domain_events)

    @classmethod
    def create(
        cls,
        workspace_id: Optional[uuid.UUID],
        source: EntityReference,
        target: EntityReference,
        relationship_type: RelationshipType,
        direction: RelationshipDirection = RelationshipDirection.DIRECTED,
        strength: float = 1.0,
        metadata: Optional[RelationshipMetadata] = None,
        relationship_id: Optional[uuid.UUID] = None,
    ) -> "RelationshipAggregate":
        rid = relationship_id or uuid.uuid4()
        now = datetime.now(timezone.utc)
        meta = metadata or RelationshipMetadata()
        agg = cls(
            id=rid,
            workspace_id=workspace_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            direction=direction,
            strength=strength,
            status=RelationshipStatus.ACTIVE,
            metadata=meta,
            version=1,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        agg._domain_events.append(
            RelationshipCreatedEvent(
                relationship_id=rid,
                workspace_id=workspace_id,
                relationship_type=relationship_type.value if hasattr(relationship_type, "value") else str(relationship_type),
                source_key=source.key,
                target_key=target.key,
                strength=agg.strength,
                confidence=meta.confidence,
                created_by=meta.created_by,
            )
        )
        return agg

    def update(
        self,
        strength: Optional[float] = None,
        direction: Optional[RelationshipDirection] = None,
        metadata_update: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        last_verified: Optional[datetime] = None,
        updated_by: Optional[str] = None,
    ) -> None:
        if self.is_deleted:
            raise GraphDomainError(f"Cannot update deleted relationship {self.id}.")

        if strength is not None:
            self.strength = max(0.0, min(1.0, float(strength)))
        if direction is not None:
            self.direction = direction

        new_conf = self.metadata.confidence if confidence is None else max(0.0, min(1.0, float(confidence)))
        new_lv = last_verified or self.metadata.last_verified
        new_extra = dict(self.metadata.extra)
        if metadata_update:
            new_extra.update(metadata_update)

        self.metadata = RelationshipMetadata(
            confidence=new_conf,
            source=self.metadata.source,
            created_by=self.metadata.created_by,
            last_verified=new_lv,
            extra=new_extra,
        )

        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

        self._domain_events.append(
            RelationshipUpdatedEvent(
                relationship_id=self.id,
                workspace_id=self.workspace_id,
                relationship_type=self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
                strength=self.strength,
                confidence=self.metadata.confidence,
                status=self.status.value if hasattr(self.status, "value") else str(self.status),
                version=self.version,
                updated_by=updated_by,
            )
        )

    def archive(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        if self.is_deleted:
            raise GraphDomainError(f"Cannot archive deleted relationship {self.id}.")
        self.status = RelationshipStatus.ARCHIVED
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
        self._domain_events.append(
            RelationshipArchivedEvent(
                relationship_id=self.id,
                workspace_id=self.workspace_id,
                reason=reason,
                actor=actor,
            )
        )

    def delete(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        self.is_deleted = True
        self.status = RelationshipStatus.DELETED
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
        self._domain_events.append(
            RelationshipDeletedEvent(
                relationship_id=self.id,
                workspace_id=self.workspace_id,
                reason=reason,
                actor=actor,
            )
        )

    def restore(self, actor: Optional[str] = None) -> None:
        self.is_deleted = False
        self.status = RelationshipStatus.ACTIVE
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
        self._domain_events.append(
            RelationshipRestoredEvent(
                relationship_id=self.id,
                workspace_id=self.workspace_id,
                actor=actor,
            )
        )

    def collect_events(self) -> List[GraphDomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": str(self.id),
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "source_node": self.source.to_dict(),
            "target_node": self.target.to_dict(),
            "relationship_type": self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
            "direction": self.direction.value if hasattr(self.direction, "value") else str(self.direction),
            "strength": self.strength,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "metadata": self.metadata.to_dict(),
            "version": self.version,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipAggregate":
        rid = uuid.UUID(str(data["relationship_id"])) if isinstance(data.get("relationship_id"), (str, uuid.UUID)) else uuid.uuid4()
        ws = uuid.UUID(str(data["workspace_id"])) if data.get("workspace_id") else None
        src_data = data.get("source_node") or data.get("source")
        src = EntityReference.from_dict(src_data) if isinstance(src_data, dict) else src_data
        tgt_data = data.get("target_node") or data.get("target")
        tgt = EntityReference.from_dict(tgt_data) if isinstance(tgt_data, dict) else tgt_data

        rel_type_raw = data.get("relationship_type")
        try:
            rel_type = RelationshipType(rel_type_raw)
        except Exception:
            rel_type = RelationshipType.CUSTOM

        dir_raw = data.get("direction", "DIRECTED")
        try:
            direction = RelationshipDirection(dir_raw)
        except Exception:
            direction = RelationshipDirection.DIRECTED

        status_raw = data.get("status", "ACTIVE")
        try:
            status = RelationshipStatus(status_raw)
        except Exception:
            status = RelationshipStatus.ACTIVE

        meta_data = data.get("metadata")
        meta = RelationshipMetadata.from_dict(meta_data) if isinstance(meta_data, dict) else RelationshipMetadata()

        ca = data.get("created_at")
        if isinstance(ca, str):
            try:
                ca = datetime.fromisoformat(ca)
            except Exception:
                ca = None
        ua = data.get("updated_at")
        if isinstance(ua, str):
            try:
                ua = datetime.fromisoformat(ua)
            except Exception:
                ua = None

        return cls(
            id=rid,
            workspace_id=ws,
            source=src,
            target=tgt,
            relationship_type=rel_type,
            direction=direction,
            strength=float(data.get("strength", 1.0)),
            status=status,
            metadata=meta,
            version=int(data.get("version", 1)),
            is_deleted=bool(data.get("is_deleted", False)),
            created_at=ca,
            updated_at=ua,
        )


# ── SQLAlchemy Database Model ─────────────────────────────────────────────────

class EntityRelationship(Base):
    """
    SQLAlchemy persistence model for Knowledge Graph edges.
    Stores relationships between business entities across workspaces.
    """
    __tablename__ = "entity_relationships"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    relationship_type = Column(String(64), nullable=False, index=True)
    source_node_type = Column(String(64), nullable=False)
    source_node_id = Column(String(128), nullable=False)
    source_label = Column(String(255), nullable=True)

    target_node_type = Column(String(64), nullable=False)
    target_node_id = Column(String(128), nullable=False)
    target_label = Column(String(255), nullable=True)

    direction = Column(String(32), nullable=False, default=RelationshipDirection.DIRECTED.value)
    strength = Column(Float, nullable=False, default=1.0)
    status = Column(String(32), nullable=False, default=RelationshipStatus.ACTIVE.value, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)

    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(128), nullable=False, default="manual_entry")
    created_by = Column(String(128), nullable=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    metadata_payload = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index(
            "ix_entity_rel_workspace_source",
            "workspace_id",
            "source_node_type",
            "source_node_id",
        ),
        Index(
            "ix_entity_rel_workspace_target",
            "workspace_id",
            "target_node_type",
            "target_node_id",
        ),
        Index(
            "ix_entity_rel_workspace_type",
            "workspace_id",
            "relationship_type",
        ),
        Index(
            "ix_entity_rel_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    def to_aggregate(self) -> RelationshipAggregate:
        try:
            rel_type = RelationshipType(self.relationship_type)
        except ValueError:
            rel_type = RelationshipType.CUSTOM

        try:
            dir_val = RelationshipDirection(self.direction)
        except ValueError:
            dir_val = RelationshipDirection.DIRECTED

        try:
            status_val = RelationshipStatus(self.status)
        except ValueError:
            status_val = RelationshipStatus.ACTIVE

        try:
            s_type = GraphNodeType(self.source_node_type)
        except ValueError:
            s_type = GraphNodeType.CUSTOM

        try:
            t_type = GraphNodeType(self.target_node_type)
        except ValueError:
            t_type = GraphNodeType.CUSTOM

        meta_dict = self.metadata_payload or {}
        extra = meta_dict.get("extra", {})

        src = EntityReference(
            entity_type=s_type,
            entity_id=self.source_node_id,
            workspace_id=self.workspace_id,
            label=self.source_label,
            properties=meta_dict.get("source_properties", {}),
        )

        tgt = EntityReference(
            entity_type=t_type,
            entity_id=self.target_node_id,
            workspace_id=self.workspace_id,
            label=self.target_label,
            properties=meta_dict.get("target_properties", {}),
        )

        meta = RelationshipMetadata(
            confidence=self.confidence,
            source=self.source,
            created_by=self.created_by,
            last_verified=self.last_verified,
            extra=extra,
        )

        return RelationshipAggregate(
            id=self.id,
            workspace_id=self.workspace_id,
            source=src,
            target=tgt,
            relationship_type=rel_type,
            direction=dir_val,
            strength=self.strength,
            status=status_val,
            metadata=meta,
            version=self.version,
            is_deleted=self.is_deleted,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


__all__ = [
    "GraphNodeType",
    "RelationshipType",
    "RelationshipDirection",
    "RelationshipStatus",
    "EntityReference",
    "RelationshipMetadata",
    "GraphDomainEvent",
    "RelationshipCreatedEvent",
    "RelationshipUpdatedEvent",
    "RelationshipArchivedEvent",
    "RelationshipDeletedEvent",
    "RelationshipRestoredEvent",
    "RelationshipAggregate",
    "EntityRelationship",
    "GraphDomainError",
    "RelationshipValidationError",
    "DuplicateRelationshipError",
    "CircularRelationshipError",
    "IncompatibleNodeTypesError",
    "RelationshipNotFoundError",
    "CrossWorkspaceRelationshipError",
]
