from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.domain.operations.models import ActionPriority, ActionStatus, ActionType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


class ActionCreatedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.created")
    source_subsystem: str = Field(default="operations_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)
    
    action_id: UUID
    action_type: ActionType
    status: ActionStatus
    priority: ActionPriority


class ActionStatusChangedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.status.changed")
    source_subsystem: str = Field(default="operations_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)
    
    action_id: UUID
    old_status: ActionStatus
    new_status: ActionStatus
    reason: Optional[str] = None


class ActionDependencyAddedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.dependency.added")
    source_subsystem: str = Field(default="operations_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)
    
    action_id: UUID
    depends_on_action_id: UUID

class ActionDependencyRemovedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.dependency.removed")
    source_subsystem: str = Field(default="operations_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)
    
    action_id: UUID
    depends_on_action_id: UUID


# ── Phase 3.5 Orchestration Events ──────────────────────────────────────────

class ActionOrchestrationStartedEvent(UniversalBaseEvent):
    """
    Emitted immediately after the Action is transitioned APPROVED → READY.
    Signals that orchestration has passed all pre-flight checks and the
    readiness corridor has officially begun.
    """
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.started")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    pinned_revision_id: str


class ActionOrchestrationHandedOffEvent(UniversalBaseEvent):
    """
    Emitted after ExecutionPort.submit() returns successfully.
    The execution_handle is the opaque token (e.g. Celery task ID)
    stored in action.execution_metadata["execution_handle"].
    """
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.handed_off")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    execution_handle: str


class ActionOrchestrationFailedEvent(UniversalBaseEvent):
    """
    Emitted when the orchestration corridor errors out after the Action
    has already been transitioned to READY or EXECUTING.
    The failed_at_status records which state the Action was in when the
    failure occurred, for observability and retry decisions.
    """
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.failed")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    failure_reason: str
    failed_at_status: ActionStatus
