"""
HunterOS Engage — Domain Events

All events fired during message processing.
Each event maps to a step in the pipeline, enabling:
  - Structured logging
  - Future async processing (Celery, Redis Streams)
  - Analytics and audit trails
  - Dashboard metrics
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


class RawWebhookEvent(UniversalBaseEvent):
    """Fired when a raw webhook payload is received from Meta."""
    category: EventCategory = Field(default=EventCategory.PLATFORM)
    event_name: str = Field(default="RawWebhookEvent")
    source_subsystem: str = Field(default="webhook")
    
    workspace_id: Optional[UUID] = None
    actor_type: Optional[ActorType] = None
    
    payload: Dict[str, Any] = Field(default_factory=dict)
    

class MessageReceived(UniversalBaseEvent):
    """Fired when a WhatsApp text message arrives at the webhook."""
    category: EventCategory = Field(default=EventCategory.CONVERSATION)
    event_name: str = Field(default="MessageReceived")
    source_subsystem: str = Field(default="webhook")
    
    wa_message_id: str = ""
    from_phone: str = ""
    content: str = ""
    timestamp: Optional[datetime] = None
    contact_name: str = ""


class MessageStored(UniversalBaseEvent):
    """Fired after the incoming message is persisted to the database."""
    category: EventCategory = Field(default=EventCategory.CONVERSATION)
    event_name: str = Field(default="MessageStored")
    source_subsystem: str = Field(default="pipeline_receive")
    
    message_id: Optional[UUID] = None
    from_phone: str = ""


class AIRequested(UniversalBaseEvent):
    """Fired immediately before the OpenAI API call is made."""
    category: EventCategory = Field(default=EventCategory.AI_DECISION)
    event_name: str = Field(default="AIRequested")
    source_subsystem: str = Field(default="pipeline_ai")
    
    from_phone: str = ""
    user_content: str = ""


class AIResponded(UniversalBaseEvent):
    """Fired after the OpenAI API returns a response."""
    category: EventCategory = Field(default=EventCategory.AI_DECISION)
    event_name: str = Field(default="AIResponded")
    source_subsystem: str = Field(default="pipeline_ai")
    
    response_content: str = ""
    model: str = ""
    total_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0


class MessageReadyToSendEvent(UniversalBaseEvent):
    """Fired when a message is ready to be sent to WhatsApp."""
    category: EventCategory = Field(default=EventCategory.CONVERSATION)
    event_name: str = Field(default="MessageReadyToSendEvent")
    source_subsystem: str = Field(default="pipeline_respond")

    to_phone: str = ""
    content: str = ""
    conversation_id: str = ""


class ReplySent(UniversalBaseEvent):
    """Fired after the WhatsApp reply has been successfully delivered."""
    category: EventCategory = Field(default=EventCategory.CONVERSATION)
    event_name: str = Field(default="ReplySent")
    source_subsystem: str = Field(default="pipeline_respond")
    
    to_phone: str = ""
    content: str = ""
    wa_message_id: Optional[str] = None


class ErrorOccurred(UniversalBaseEvent):
    """Fired when a pipeline stage encounters an unhandled error."""
    category: EventCategory = Field(default=EventCategory.PLATFORM)
    event_name: str = Field(default="ErrorOccurred")
    source_subsystem: str = Field(default="pipeline")
    
    stage: str = ""
    error_message: str = ""
    error_type: str = ""
    from_phone: str = ""
