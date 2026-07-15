from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.timeline.models import TimelineSeverity
from app.events.model.actor_types import ActorType


class TimelineEntryResponse(BaseModel):
    timeline_id: UUID
    event_id: UUID
    workspace_id: UUID
    customer_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    
    occurred_at: datetime
    
    # Generated from strategy formatters
    activity_title: str
    activity_description: str
    activity_type: str
    
    severity: TimelineSeverity
    actor_type: ActorType
    actor_id: Optional[str] = None
    source_subsystem: str

    class Config:
        from_attributes = True
