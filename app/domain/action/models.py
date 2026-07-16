import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ActionPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ActionExecution(Base):
    """
    Core model for managing executable operational actions in HunterOS.
    """
    __tablename__ = "action_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Traceability & Idempotency
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=False, index=True)
    
    # Target
    connector_id = Column(String(100), nullable=False)      # The specific connection
    target_system = Column(String(50), nullable=False)      # e.g., "crm", "email"
    
    # Action Payload
    action_type = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    
    status = Column(String(50), nullable=False, default=ActionStatus.PENDING.value)
    priority = Column(String(50), nullable=False, default=ActionPriority.NORMAL.value)
    
    requested_by = Column(String(100), nullable=False)      # e.g. "RecommendationEngine", "User:uuid"
    
    # Timing
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    queued_duration_ms = Column(Integer, nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)
    
    # Execution Details
    execution_result = Column(JSON, nullable=True)          # ExecutionResult schema
    error_details = Column(String(2000), nullable=True)
    
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    
    engine_version = Column(String(50), nullable=False, default="1.0.0")
    connector_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('workspace_id', 'idempotency_key', name='uq_action_idempotency'),
    )
