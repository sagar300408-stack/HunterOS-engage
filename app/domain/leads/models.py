import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base

class LeadQualificationSnapshot(Base):
    """
    Persisted qualification snapshot for a customer at a given point in time.
    """
    __tablename__ = "lead_qualification_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    
    score = Column(Integer, nullable=False)
    grade = Column(String(5), nullable=False)
    buying_stage = Column(String(100), nullable=True)
    urgency = Column(String(50), nullable=False)
    intent = Column(String(100), nullable=False)
    budget = Column(String(255), nullable=True)
    timeline = Column(String(255), nullable=True)
    next_action = Column(String(255), nullable=True)
    qualified = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_lead_qualification_snapshots_customer_id", "customer_id"),
        Index("ix_lead_qualification_snapshots_workspace_id", "workspace_id"),
        Index("ix_lead_qualification_snapshots_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<LeadQualificationSnapshot customer_id={self.customer_id} score={self.score} grade={self.grade}>"
