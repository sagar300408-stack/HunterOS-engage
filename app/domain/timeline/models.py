import enum
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.conversations.models import Base
from app.events.model.actor_types import ActorType


class TimelineSeverity(enum.Enum):
    INFO = "info"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"

    timeline_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    
    workspace_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    conversation_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    lead_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[TimelineSeverity] = mapped_column(Enum(TimelineSeverity), default=TimelineSeverity.NORMAL)
    
    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    
    source_subsystem: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Stores dynamic payload parameters needed to generate the human-readable text
    structured_data: Mapped[Dict[str, Any]] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)
