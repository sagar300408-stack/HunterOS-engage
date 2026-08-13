import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Index,
    text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base


class OrchestrationRunState(str, enum.Enum):
    """Lifecycle states of an OrchestrationRun."""
    CREATED = "CREATED"
    READY = "READY"
    STARTING = "STARTING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class OrchestrationAttemptState(str, enum.Enum):
    """Lifecycle states of a single execution Attempt."""
    STARTING = "STARTING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class OrchestrationRun(Base):
    """
    Represents the overall orchestration lifecycle for a single authorized
    Action version. Orchestration runs manage multiple attempts (retries),
    timeouts, and cancellation semantics, independent of the business Action state.
    """
    __tablename__ = "orchestration_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action_id = Column(UUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True)
    action_version = Column(Integer, nullable=False)
    state = Column(Enum(OrchestrationRunState, name="orchestration_run_state"), nullable=False, default=OrchestrationRunState.CREATED)
    
    max_attempts = Column(Integer, nullable=False, default=1)
    attempt_count = Column(Integer, nullable=False, default=0)
    
    failure_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to attempts
    attempts = relationship("OrchestrationAttempt", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        # Guarantee strictly one active run per Action at any given time.
        Index(
            "ix_orchestration_runs_active_unique",
            "workspace_id", "action_id",
            unique=True,
            postgresql_where=text("state IN ('CREATED', 'READY', 'STARTING', 'EXECUTING')")
        ),
    )


class OrchestrationAttempt(Base):
    """
    Represents a single physical handoff attempt to the ExecutionPort.
    """
    __tablename__ = "orchestration_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    
    state = Column(Enum(OrchestrationAttemptState, name="orchestration_attempt_state"), nullable=False, default=OrchestrationAttemptState.STARTING)
    
    execution_handle = Column(String, nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    
    outcome = Column(String, nullable=True)
    failure_type = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    retryable = Column(Boolean, nullable=True)
    
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationship back to run
    run = relationship("OrchestrationRun", back_populates="attempts")
