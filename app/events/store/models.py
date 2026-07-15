from sqlalchemy import Column, DateTime, Index, Integer, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.domain.conversations.models import Base

class EventRecord(Base):
    """
    Immutable persistent record of every business event published to the Event Bus.
    Serves as the permanent operational memory for HunterOS.
    """
    __tablename__ = "event_store"

    # Identity Layer
    event_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    causation_id = Column(UUID(as_uuid=True), nullable=True)

    # Context Layer
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    lead_id = Column(UUID(as_uuid=True), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(255), nullable=True)
    source_subsystem = Column(String(100), nullable=False)

    # Content Layer
    category = Column(String(50), nullable=False)
    event_name = Column(String(100), nullable=False)
    
    # Store the entire event as a JSON document for perfect fidelity
    payload = Column(JSONB().with_variant(JSON(), 'sqlite'), nullable=False)
    
    # Extract metadata out to a separate column to avoid SQLAlchemy reserved word 'metadata'
    metadata_payload = Column(JSONB().with_variant(JSON(), 'sqlite'), nullable=False, default=dict)

    # AI Decision Fields for explainability
    ai_model_version = Column(String(100), nullable=True)
    ai_reason = Column(String, nullable=True)
    
    # Indexes for fast historical queries
    __table_args__ = (
        Index("ix_event_store_workspace_id", "workspace_id"),
        Index("ix_event_store_occurred_at", "occurred_at"),
        Index("ix_event_store_category", "category"),
        Index("ix_event_store_event_name", "event_name"),
        Index("ix_event_store_correlation_id", "correlation_id"),
        Index("ix_event_store_customer_id", "customer_id"),
        Index("ix_event_store_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<EventRecord id={self.event_id} name={self.event_name} category={self.category}>"
