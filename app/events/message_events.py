"""
HunterOS Engage — Domain Events

All events fired during message processing.
Each event maps to a step in the pipeline, enabling:
  - Structured logging
  - Future async processing (Celery, Redis Streams)
  - Analytics and audit trails
  - Dashboard metrics
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.events.base import BaseEvent


@dataclass
class MessageReceived(BaseEvent):
    """Fired when a WhatsApp text message arrives at the webhook."""

    wa_message_id: str = ""
    from_phone: str = ""
    content: str = ""
    timestamp: Optional[datetime] = None
    contact_name: str = ""


@dataclass
class MessageStored(BaseEvent):
    """Fired after the incoming message is persisted to the database."""

    message_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    from_phone: str = ""


@dataclass
class AIRequested(BaseEvent):
    """Fired immediately before the OpenAI API call is made."""

    conversation_id: Optional[UUID] = None
    from_phone: str = ""
    user_content: str = ""


@dataclass
class AIResponded(BaseEvent):
    """Fired after the OpenAI API returns a response."""

    conversation_id: Optional[UUID] = None
    response_content: str = ""
    model: str = ""
    total_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class ReplySent(BaseEvent):
    """Fired after the WhatsApp reply has been successfully delivered."""

    to_phone: str = ""
    content: str = ""
    wa_message_id: Optional[str] = None


@dataclass
class ErrorOccurred(BaseEvent):
    """Fired when a pipeline stage encounters an unhandled error."""

    stage: str = ""
    error_message: str = ""
    error_type: str = ""
    from_phone: str = ""
