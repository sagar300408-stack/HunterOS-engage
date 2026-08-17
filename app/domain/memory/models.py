"""
HunterOS Engage — Memory Domain Models (Core Memory Foundation & Aggregate Root)

Foundational memory infrastructure storing structured customer knowledge
independently of conversation history.

Data Models:
  1. CustomerMemory              — Aggregate Root holding latest canonical memory_payload, revision_id, and lifecycle_status
  2. CustomerMemoryVersion       — Immutable Aggregate Snapshot archive (snapshot_payload, schema_version, snapshot_hash)
  3. CustomerMemoryTimelineEvent — Industry-agnostic append-only timeline event log
  4. MemoryChangeLog             — Field-level granular delta tracking with changed_module attribution
  5. MemoryIdempotencyRecord     — Request deduplication and safe retry cache with expires_at
"""

import copy
import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class MemoryDomainError(ValueError):
    """Base exception for all memory domain errors."""
    pass


class MemoryConcurrencyConflictError(MemoryDomainError):
    """Raised when an update fails due to optimistic concurrency control (revision_id mismatch)."""

    def __init__(
        self,
        customer_id: uuid.UUID,
        expected_revision: Optional[str],
        actual_revision: str,
        actual_version: int,
        message: Optional[str] = None,
    ):
        self.customer_id = customer_id
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        self.actual_version = actual_version
        super().__init__(
            message
            or f"Concurrency conflict on CustomerMemory {customer_id}: expected revision '{expected_revision}', "
            f"current revision is '{actual_revision}' (v{actual_version})."
        )


class InvalidLifecycleTransitionError(MemoryDomainError):
    """Raised when an illegal lifecycle status transition is attempted."""

    def __init__(self, current_status: str, target_status: str, reason: Optional[str] = None):
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason
        super().__init__(
            f"Invalid lifecycle transition from '{current_status}' to '{target_status}'"
            + (f": {reason}" if reason else ".")
        )


class MemoryLockedError(MemoryDomainError):
    """Raised when a mutation is attempted on a locked or read-only customer memory."""

    def __init__(self, customer_id: uuid.UUID, status: str):
        self.customer_id = customer_id
        self.status = status
        super().__init__(
            f"Cannot mutate CustomerMemory {customer_id}: record is in '{status}' status."
        )


# ── Enums ─────────────────────────────────────────────────────────────────────

class LifecycleStatus(str, enum.Enum):
    """Memory lifecycle state machine states."""
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    ARCHIVED = "ARCHIVED"
    SOFT_DELETED = "SOFT_DELETED"
    RESTORING = "RESTORING"
    MIGRATING = "MIGRATING"


class MemoryTimelineCategory(str, enum.Enum):
    """Industry-agnostic categories for memory timeline events."""
    LIFECYCLE = "LIFECYCLE"
    PROFILE = "PROFILE"
    PREFERENCE = "PREFERENCE"
    RELATIONSHIP = "RELATIONSHIP"
    FINANCIAL = "FINANCIAL"
    BUSINESS = "BUSINESS"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class MemoryImportance(str, enum.Enum):
    """Importance levels for memory timeline events."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MemoryEventType(str, enum.Enum):
    """Standard timeline event types."""
    customer_created = "customer_created"
    conversation_started = "conversation_started"
    memory_created = "memory_created"
    memory_updated = "memory_updated"
    memory_soft_deleted = "memory_soft_deleted"
    memory_restored = "memory_restored"
    memory_status_changed = "memory_status_changed"


class ChangeType(str, enum.Enum):
    """Field-level change operation type."""
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


# ── Aggregate Root: CustomerMemory ────────────────────────────────────────────

class CustomerMemory(Base):
    """
    Foundational customer memory entity (Aggregate Root).

    Holds the latest canonical structured memory payload independently
    of conversation history, and encapsulates domain invariants, versioning,
    optimistic concurrency control, and lifecycle transitions.
    """

    __tablename__ = "customer_memory"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    workspace_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    memory_payload = Column(
        JSONB,
        nullable=False,
        default=dict,
    )
    version_number = Column(
        Integer,
        nullable=False,
        default=1,
    )
    revision_id = Column(
        String(64),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    __mapper_args__ = {
        "version_id_col": revision_id,
        "version_id_generator": False,
    }

    lifecycle_status = Column(
        Enum(LifecycleStatus, name="memory_lifecycle_status"),
        nullable=False,
        default=LifecycleStatus.ACTIVE,
        index=True,
    )
    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="memory")
    versions = relationship(
        "CustomerMemoryVersion",
        back_populates="memory",
        cascade="all, delete-orphan",
        order_by="CustomerMemoryVersion.version_number.desc()",
    )
    timeline_events = relationship(
        "CustomerMemoryTimelineEvent",
        back_populates="memory",
        cascade="all, delete-orphan",
        order_by="CustomerMemoryTimelineEvent.created_at.desc()",
    )
    change_logs = relationship(
        "MemoryChangeLog",
        back_populates="memory",
        cascade="all, delete-orphan",
        order_by="MemoryChangeLog.created_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerMemory id={self.id} customer_id={self.customer_id} "
            f"v={self.version_number} rev={self.revision_id[:8]} "
            f"status={self.lifecycle_status} deleted={self.is_deleted}>"
        )

    # ── Aggregate Domain Methods ──────────────────────────────────────────────

    def _verify_mutation_allowed(
        self,
        expected_revision_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> None:
        """Enforces domain invariants before any state-changing mutation."""
        if self.lifecycle_status in (LifecycleStatus.LOCKED, LifecycleStatus.ARCHIVED, LifecycleStatus.MIGRATING):
            raise MemoryLockedError(self.customer_id, self.lifecycle_status.value)

        if self.is_deleted or self.lifecycle_status == LifecycleStatus.SOFT_DELETED:
            raise MemoryDomainError(
                f"CustomerMemory {self.customer_id} is soft-deleted. Restore it before updating."
            )

        # Optimistic Concurrency Control
        if expected_revision_id is not None and expected_revision_id != self.revision_id:
            raise MemoryConcurrencyConflictError(
                customer_id=self.customer_id,
                expected_revision=expected_revision_id,
                actual_revision=self.revision_id,
                actual_version=self.version_number,
            )

        if expected_version is not None and expected_version != self.version_number:
            raise MemoryConcurrencyConflictError(
                customer_id=self.customer_id,
                expected_revision=f"v{expected_version}",
                actual_revision=f"v{self.version_number}",
                actual_version=self.version_number,
                message=f"Version conflict on CustomerMemory {self.customer_id}: expected v{expected_version}, current is v{self.version_number}.",
            )

    def _advance_revision(self) -> None:
        """Generates a fresh revision ID and increments the aggregate version."""
        self.version_number += 1
        self.revision_id = str(uuid.uuid4())
        self.updated_at = datetime.now(timezone.utc)

    def update_payload(
        self,
        delta_payload: Dict[str, Any],
        source: str = "API",
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        expected_revision_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a partial update (PATCH) by deep-merging delta_payload into memory_payload.
        Returns a deep copy of the old_payload for audit diffing.
        """
        self._verify_mutation_allowed(expected_revision_id, expected_version)
        old_payload = copy.deepcopy(self.memory_payload or {})

        merged = copy.deepcopy(old_payload)
        self._deep_merge_dict(merged, delta_payload)
        self.memory_payload = merged

        self._advance_revision()
        return old_payload

    def replace_payload(
        self,
        new_payload: Dict[str, Any],
        source: str = "API",
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        expected_revision_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a complete replacement (PUT) of memory_payload.
        Returns a deep copy of the old_payload for audit diffing.
        """
        self._verify_mutation_allowed(expected_revision_id, expected_version)
        old_payload = copy.deepcopy(self.memory_payload or {})

        self.memory_payload = copy.deepcopy(new_payload)
        self._advance_revision()
        return old_payload

    def soft_delete(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        """Marks memory as soft-deleted and transitions status to SOFT_DELETED."""
        if self.lifecycle_status == LifecycleStatus.LOCKED:
            raise MemoryLockedError(self.customer_id, self.lifecycle_status.value)
        if self.is_deleted:
            return  # Idempotent

        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.lifecycle_status = LifecycleStatus.SOFT_DELETED
        self._advance_revision()

    def restore(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        """Restores a soft-deleted memory back to ACTIVE."""
        if not self.is_deleted and self.lifecycle_status == LifecycleStatus.ACTIVE:
            return  # Idempotent

        self.is_deleted = False
        self.deleted_at = None
        self.lifecycle_status = LifecycleStatus.ACTIVE
        self._advance_revision()

    def archive(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        """Transitions memory into ARCHIVED read-only state."""
        self.transition_status(LifecycleStatus.ARCHIVED, reason=reason, actor=actor)

    def lock(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        """Transitions memory into LOCKED administrative lock state."""
        self.transition_status(LifecycleStatus.LOCKED, reason=reason, actor=actor)

    def unlock(self, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        """Unlocks a LOCKED memory back to ACTIVE."""
        if self.lifecycle_status != LifecycleStatus.LOCKED:
            raise InvalidLifecycleTransitionError(
                self.lifecycle_status.value,
                LifecycleStatus.ACTIVE.value,
                "Memory is not locked.",
            )
        self.lifecycle_status = LifecycleStatus.ACTIVE
        self._advance_revision()

    def transition_status(
        self,
        target_status: LifecycleStatus,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> None:
        """
        Validates and executes lifecycle state transition.
        Allowed transitions:
          ACTIVE       -> SOFT_DELETED, ARCHIVED, LOCKED, MIGRATING
          SOFT_DELETED -> RESTORING -> ACTIVE
          ARCHIVED     -> ACTIVE
          LOCKED       -> ACTIVE
          MIGRATING    -> ACTIVE
        """
        current = self.lifecycle_status

        if current == target_status:
            return  # Idempotent

        allowed = {
            LifecycleStatus.ACTIVE: {
                LifecycleStatus.SOFT_DELETED,
                LifecycleStatus.ARCHIVED,
                LifecycleStatus.LOCKED,
                LifecycleStatus.MIGRATING,
            },
            LifecycleStatus.SOFT_DELETED: {
                LifecycleStatus.RESTORING,
                LifecycleStatus.ACTIVE,
            },
            LifecycleStatus.RESTORING: {
                LifecycleStatus.ACTIVE,
            },
            LifecycleStatus.ARCHIVED: {
                LifecycleStatus.ACTIVE,
            },
            LifecycleStatus.LOCKED: {
                LifecycleStatus.ACTIVE,
            },
            LifecycleStatus.MIGRATING: {
                LifecycleStatus.ACTIVE,
            },
        }

        if target_status not in allowed.get(current, set()):
            raise InvalidLifecycleTransitionError(
                current.value,
                target_status.value,
                f"Transition from {current.value} to {target_status.value} is not permitted.",
            )

        self.lifecycle_status = target_status
        if target_status == LifecycleStatus.SOFT_DELETED:
            self.is_deleted = True
            self.deleted_at = datetime.now(timezone.utc)
        elif target_status in (LifecycleStatus.ACTIVE, LifecycleStatus.RESTORING):
            self.is_deleted = False
            self.deleted_at = None

        self._advance_revision()

    @staticmethod
    def _deep_merge_dict(target: Dict[str, Any], delta: Dict[str, Any]) -> None:
        """Recursively merges delta dictionary into target dictionary in-place."""
        for key, value in delta.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                CustomerMemory._deep_merge_dict(target[key], value)
            else:
                target[key] = copy.deepcopy(value)


# ── Aggregate Snapshot: CustomerMemoryVersion ─────────────────────────────────

class CustomerMemoryVersion(Base):
    """
    Immutable Aggregate Snapshot of CustomerMemory state at a specific version.

    Stores:
      - snapshot_data (complete normalized frozen memory_payload)
      - schema_version (semantic versioning for schema evolution)
      - snapshot_hash (SHA-256 checksum for audit & data integrity)
    """

    __tablename__ = "customer_memory_versions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_memory.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(
        Integer,
        nullable=False,
    )
    snapshot_data = Column(
        JSONB,
        nullable=False,
    )
    schema_version = Column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    snapshot_hash = Column(
        String(64),
        nullable=False,
    )
    reason = Column(
        Text,
        nullable=True,
    )
    trigger = Column(
        String(64),
        nullable=False,
        default="manual_update",
    )
    created_by = Column(
        String(128),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    memory = relationship("CustomerMemory", back_populates="versions")
    customer = relationship("Customer", back_populates="memory_versions")

    __table_args__ = (
        Index("ix_memory_versions_cust_ver", "customer_id", "version_number"),
    )

    def __repr__(self) -> str:
        return f"<CustomerMemoryVersion customer_id={self.customer_id} v={self.version_number} hash={self.snapshot_hash[:8]}>"


# ── Append-Only Timeline: CustomerMemoryTimelineEvent ─────────────────────────

class CustomerMemoryTimelineEvent(Base):
    """
    Append-only chronological timeline event log for memory changes & customer events.
    """

    __tablename__ = "customer_memory_timeline_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_memory.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(
        Enum(MemoryTimelineCategory, name="memory_timeline_category"),
        nullable=False,
        index=True,
    )
    event_type = Column(
        String(64),
        nullable=False,
        index=True,
    )
    title = Column(
        String(255),
        nullable=False,
    )
    description = Column(
        Text,
        nullable=True,
    )
    source = Column(
        String(64),
        nullable=False,
        default="system",
    )
    importance = Column(
        Enum(MemoryImportance, name="memory_importance"),
        nullable=False,
        default=MemoryImportance.MEDIUM,
    )
    payload = Column(
        JSONB,
        nullable=True,
        default=dict,
    )
    version_number = Column(
        Integer,
        nullable=False,
        default=1,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    memory = relationship("CustomerMemory", back_populates="timeline_events")
    customer = relationship("Customer", back_populates="memory_events")

    __table_args__ = (
        Index("ix_memory_timeline_cust_cat", "customer_id", "category"),
        Index("ix_memory_timeline_cust_created", "customer_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CustomerMemoryTimelineEvent category={self.category} type={self.event_type} customer_id={self.customer_id}>"


# Alias for timeline events
CustomerMemoryEvent = CustomerMemoryTimelineEvent


# ── Append-Only Change Log: MemoryChangeLog ───────────────────────────────────

class MemoryChangeLog(Base):
    """
    Granular field-level delta log tracking exact property changes with module attribution.
    """

    __tablename__ = "memory_change_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_memory.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(
        Integer,
        nullable=False,
    )
    field_path = Column(
        String(255),
        nullable=False,
        index=True,
    )
    old_value = Column(
        JSONB,
        nullable=True,
    )
    new_value = Column(
        JSONB,
        nullable=True,
    )
    change_type = Column(
        Enum(ChangeType, name="memory_change_type"),
        nullable=False,
    )
    changed_module = Column(
        String(64),
        nullable=False,
        default="Manual Update",
    )
    changed_by = Column(
        String(128),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    memory = relationship("CustomerMemory", back_populates="change_logs")

    __table_args__ = (
        Index("ix_memory_changelog_cust_ver", "customer_id", "version_number"),
        Index("ix_memory_changelog_cust_field", "customer_id", "field_path"),
    )

    def __repr__(self) -> str:
        return f"<MemoryChangeLog path={self.field_path} type={self.change_type} module={self.changed_module}>"


# ── Idempotency Record: MemoryIdempotencyRecord ───────────────────────────────

class MemoryIdempotencyRecord(Base):
    """
    Idempotency record for duplicate detection, retry safety, and replay suppression.
    """

    __tablename__ = "memory_idempotency_records"

    idempotency_key = Column(
        String(128),
        primary_key=True,
        nullable=False,
    )
    request_hash = Column(
        String(64),
        nullable=False,
        index=True,
    )
    response_status = Column(
        Integer,
        nullable=False,
    )
    response_body = Column(
        JSONB,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            return datetime.utcnow() >= self.expires_at
        return now >= self.expires_at

    def __repr__(self) -> str:
        return f"<MemoryIdempotencyRecord key={self.idempotency_key} status={self.response_status}>"
