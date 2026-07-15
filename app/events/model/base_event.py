from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.events.model.actor_types import ActorType
from app.events.model.categories import EventCategory


class UniversalBaseEvent(BaseModel):
    """
    The foundational Event Model for HunterOS.
    All platform events inherit from this model or a category-specific subclass.
    """

    # Identity Layer
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: int = Field(default=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None

    # Context Layer
    workspace_id: UUID
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    actor_type: ActorType
    actor_id: Optional[str] = None
    source_subsystem: str

    # Content Layer
    category: EventCategory
    event_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # AI Decision Fields (Populated only for AI events)
    ai_model_version: Optional[str] = None
    ai_reason: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_evidence: Optional[List[Any]] = None
    ai_inputs: Optional[Dict[str, Any]] = None
    ai_outputs: Optional[Dict[str, Any]] = None

    class Config:
        # Prevent adding arbitrary fields; subclass for specific payloads
        extra = "forbid"
