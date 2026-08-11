from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.domain.operations.models import ActionPriority, ActionStatus, ActionType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory


class ActionCreatedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.created")
    
    action_id: UUID
    action_type: ActionType
    status: ActionStatus
    priority: ActionPriority


class ActionStatusChangedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.status.changed")
    
    action_id: UUID
    old_status: ActionStatus
    new_status: ActionStatus
    reason: Optional[str] = None


class ActionDependencyAddedEvent(UniversalBaseEvent):
    category: EventCategory = Field(default=EventCategory.ACTION)
    event_name: str = Field(default="action.dependency.added")
    
    action_id: UUID
    depends_on_action_id: UUID
