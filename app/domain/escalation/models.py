import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Enum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.domain.conversations.models import Base

class EscalationStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    resolved = "resolved"
    dismissed = "dismissed"

class HumanEscalation(Base):
    __tablename__ = "human_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True,
    )
    intent_history_id = Column(
        UUID(as_uuid=True),
        ForeignKey("intent_history.id", ondelete="CASCADE"),
        nullable=True,
    )
    trigger_intent = Column(String(100), nullable=False)
    trigger_next_action = Column(String(255), nullable=False)
    status = Column(
        Enum(EscalationStatus, name="escalationstatus"),
        nullable=False,
        default=EscalationStatus.pending,
    )
    context_snapshot = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolution_note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_human_escalations_workspace_id", "workspace_id"),
        Index("ix_human_escalations_customer_id", "customer_id"),
        Index("ix_human_escalations_status", "status"),
        Index("ix_human_escalations_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<HumanEscalation customer_id={self.customer_id} status={self.status}>"
