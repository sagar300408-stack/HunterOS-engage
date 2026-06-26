"""
Pydantic schemas for the conversations domain.
Used for API I/O, internal DTOs, and service-layer communication.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageDirectionEnum(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"


# ── AI Metadata ───────────────────────────────────────────────────────────────

class AIMetadataSchema(BaseModel):
    """Structured AI response metadata captured per outgoing message."""

    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    finish_reason: Optional[str] = None
    prompt_version: str = "v1"

    class Config:
        from_attributes = True


# ── Message ───────────────────────────────────────────────────────────────────

class MessageSchema(BaseModel):
    """Full message representation including optional AI metadata."""

    id: UUID
    conversation_id: UUID
    direction: MessageDirectionEnum
    content: str
    wa_message_id: Optional[str] = None
    timestamp: datetime
    ai_metadata: Optional[AIMetadataSchema] = None

    class Config:
        from_attributes = True


# ── Conversation ──────────────────────────────────────────────────────────────

class ConversationSchema(BaseModel):
    """Full conversation representation with embedded messages."""

    id: UUID
    customer_phone: str
    created_at: datetime
    messages: list[MessageSchema] = []

    class Config:
        from_attributes = True


# ── Internal DTOs (Service Layer) ─────────────────────────────────────────────

class SaveMessageDTO(BaseModel):
    """
    DTO passed to message_service.save_message().
    Decouples the pipeline from direct ORM access.
    """

    conversation_id: UUID
    direction: MessageDirectionEnum
    content: str
    wa_message_id: Optional[str] = None
    timestamp: datetime
    ai_metadata: Optional[AIMetadataSchema] = None
