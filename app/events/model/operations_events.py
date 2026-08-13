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

class ActionOrchestrationRunStartedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.run.started")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    run_id: UUID
    action_version: int


class ActionOrchestrationRunCompletedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.run.completed")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    run_id: UUID
    action_version: int


class ActionOrchestrationRunFailedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.run.failed")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    run_id: UUID
    action_version: int
    failure_reason: Optional[str] = None


class ActionOrchestrationRunTimedOutEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.run.timed_out")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    run_id: UUID
    action_version: int


class ActionOrchestrationRunCancelledEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.orchestration.run.cancelled")
    source_subsystem: str = Field(default="orchestration_engine")
    actor_type: ActorType = Field(default=ActorType.SYSTEM)

    action_id: UUID
    run_id: UUID
    action_version: int

