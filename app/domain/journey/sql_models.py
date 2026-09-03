import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Index, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from app.domain.conversations.models import Base

class JourneyStateModel(Base):
    __tablename__ = "journey_states"

    journey_instance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    entity_id = Column(String(255), nullable=False)
    current_stage = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    
    # Store the entire dataclass structure here to avoid 10 table joins
    state_data = Column(LargeBinary, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_journey_states_workspace_entity", "workspace_id", "entity_id"),
    )
