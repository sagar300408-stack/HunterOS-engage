import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.dashboard.models import DEFAULT_WORKSPACE_ID

class FollowUpQueue(Base):
    __tablename__ = "followup_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Engine state
    status = Column(String(50), nullable=False, default="scheduled")  # scheduled, executing, sent, cancelled, paused, replied
    reason = Column(String(255), nullable=False)
    strategy = Column(String(100), nullable=True)
    priority = Column(String(50), nullable=False, default="normal")
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    
    # Message content
    generated_message = Column(Text, nullable=True)
    final_message = Column(Text, nullable=True)  # After human edit
    channel = Column(String(50), nullable=False, default="whatsapp")
    
    # AI Metadata & Explainability
    explainability_report = Column(JSONB, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    risk_score = Column(Integer, nullable=True)
    
    # Execution Tracking
    human_paused = Column(Boolean, nullable=False, default=False)
    human_edited = Column(Boolean, nullable=False, default=False)
    cancellation_reason = Column(String(255), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer")
    executions = relationship("FollowUpExecution", back_populates="followup", cascade="all, delete-orphan")


class FollowUpExecution(Base):
    __tablename__ = "followup_executions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    followup_id = Column(UUID(as_uuid=True), ForeignKey("followup_queue.id", ondelete="CASCADE"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    outcome = Column(String(50), nullable=False)  # sent, failed
    channel = Column(String(50), nullable=False)
    message_sent = Column(Text, nullable=False)
    
    provider_message_id = Column(String(255), nullable=True)
    failure_reason = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    followup = relationship("FollowUpQueue", back_populates="executions")


class LeadHealthScore(Base):
    __tablename__ = "lead_health_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    score = Column(Integer, nullable=False)
    band = Column(String(50), nullable=False)  # Excellent, Good, Moderate, At Risk, Critical
    reasons = Column(JSONB, nullable=False, default=list)
    positive_signals = Column(JSONB, nullable=False, default=list)
    recommendation = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalesMemoryTimeline(Base):
    __tablename__ = "sales_memory_timeline"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    
    event_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)  # Extra context
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
