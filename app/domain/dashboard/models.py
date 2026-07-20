import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID

# ── PipelineEvent ──────────────────────────────────────────────────────────────

class PipelineStep(str, enum.Enum):
    message_received   = "message_received"
    customer_identified = "customer_identified"
    memory_loaded      = "memory_loaded"
    intent_extracted   = "intent_extracted"
    response_generated = "response_generated"
    memory_updated     = "memory_updated"
    reply_sent         = "reply_sent"
    error              = "error"


class PipelineEvent(Base):
    """
    Step-level execution record for one incoming message.
    """
    __tablename__ = "pipeline_events"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    message_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    step         = Column(
        Enum(PipelineStep, name="pipelinestep"),
        nullable=False,
    )
    status       = Column(String(20), nullable=False, default="success")  # success | error
    duration_ms  = Column(Integer, nullable=True)
    payload      = Column(JSONB, nullable=True)   # step-specific data snapshot
    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # Relationship
    message = relationship("Message", back_populates="pipeline_events")

    __table_args__ = (
        Index("ix_pipeline_events_message_id", "message_id"),
        Index("ix_pipeline_events_workspace_id", "workspace_id"),
        Index("ix_pipeline_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PipelineEvent step={self.step} status={self.status} msg={self.message_id}>"


# ── BackgroundJob ──────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"
    cancelled = "cancelled"


class BackgroundJob(Base):
    """
    Queue monitor entry for async background jobs.
    """
    __tablename__ = "background_jobs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    job_type     = Column(String(100), nullable=False)   # e.g. "followup_schedule", "crm_sync"
    status       = Column(
        Enum(JobStatus, name="jobstatus"),
        nullable=False,
        default=JobStatus.pending,
    )
    run_count    = Column(Integer, nullable=False, default=0)
    last_error   = Column(Text, nullable=True)
    job_metadata = Column(JSONB, nullable=True)   # renamed from 'metadata' — reserved by SQLAlchemy
    is_demo      = Column(Boolean, default=False, server_default="false", nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_background_jobs_workspace_id", "workspace_id"),
        Index("ix_background_jobs_status", "status"),
        Index("ix_background_jobs_scheduled_at", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<BackgroundJob type={self.job_type} status={self.status}>"
