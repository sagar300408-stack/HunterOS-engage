"""
HunterOS Engage — Memory Domain Events

Domain event models capturing lifecycle state changes of CustomerMemory Aggregate Root.
Every event carries complete standard metadata including tenant_id context.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory

NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")


class BaseMemoryDomainEvent(UniversalBaseEvent):
    """
    Base domain event for the Customer Memory aggregate root.
    Extends UniversalBaseEvent with tenant_id, aggregate metadata, and payload.
    """
    workspace_id: UUID = Field(default=NIL_UUID)
    category: EventCategory = EventCategory.CUSTOMER
    source_subsystem: str = "memory_engine"
    actor_type: ActorType = ActorType.SYSTEM

    # Aggregate & Tenant Metadata
    aggregate_id: UUID
    aggregate_type: str = "CustomerMemory"
    tenant_id: Optional[UUID] = None
    version: int = 1
    event_type: str

    # Payload & Change Content
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class MemoryCreatedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when a new CustomerMemory aggregate is initialized."""
    event_name: str = "memory.created"
    event_type: str = "memory.created"


class MemoryUpdatedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is partially updated (PATCH) or replaced (PUT)."""
    event_name: str = "memory.updated"
    event_type: str = "memory.updated"
    old_version: int = 1
    new_version: int = 2
    changed_fields: List[str] = Field(default_factory=list)


class MemoryDeletedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is soft-deleted."""
    event_name: str = "memory.deleted"
    event_type: str = "memory.deleted"
    reason: Optional[str] = None


class MemoryRestoredDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is restored from soft-deleted state."""
    event_name: str = "memory.restored"
    event_type: str = "memory.restored"
    reason: Optional[str] = None


class MemoryVersionCreatedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when an immutable Aggregate Snapshot (CustomerMemoryVersion) is created."""
    event_name: str = "memory.version_created"
    event_type: str = "memory.version_created"
    version_number: int = 1
    snapshot_hash: str = ""


class MemoryStatusChangedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory undergoes a lifecycle status transition."""
    event_name: str = "memory.status_changed"
    event_type: str = "memory.status_changed"
    previous_status: str = "ACTIVE"
    current_status: str = "ACTIVE"
    reason: Optional[str] = None


class MemoryLockedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is administratively locked."""
    event_name: str = "memory.locked"
    event_type: str = "memory.locked"
    reason: Optional[str] = None


class MemoryUnlockedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is unlocked."""
    event_name: str = "memory.unlocked"
    event_type: str = "memory.unlocked"
    reason: Optional[str] = None


class MemoryArchivedDomainEvent(BaseMemoryDomainEvent):
    """Emitted when CustomerMemory is archived."""
    event_name: str = "memory.archived"
    event_type: str = "memory.archived"
    reason: Optional[str] = None
