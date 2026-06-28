"""
HunterOS Engage — Dashboard Domain Models

Four models introduced in Phase 4:
  - User         : Dashboard operators with roles (RBAC)
  - AuditLog     : Immutable record of every manual mutation
  - PipelineEvent: Step-level execution log for Event Replay
  - BackgroundJob: Queue monitor for async jobs (Phase 5/6 ready)

All models carry workspace_id for multi-tenancy.
"""

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

# ── Default workspace for single-tenant / development mode ────────────────────
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Role enum ──────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    founder = "Founder"
    admin   = "Admin"
    sales   = "Sales"
    support = "Support"
    reader  = "Read-only Viewer"


# ── Permission helpers ─────────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.founder: {"*"},           # all permissions
    UserRole.admin:   {"*"},
    UserRole.sales:   {
        "edit_memory", "add_note", "change_lead_stage", "view_all",
    },
    UserRole.support: {
        "edit_memory", "add_note", "view_all",
    },
    UserRole.reader:  {"view_all"},
}


def role_can(role: UserRole, permission: str) -> bool:
    """Return True if this role has the requested permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


# ── User ───────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Dashboard operator account.

    Passwords are stored as bcrypt hashes — never plaintext.
    workspace_id scopes the operator to a single tenant.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        default=DEFAULT_WORKSPACE_ID,
    )
    email        = Column(String(255), nullable=False, unique=True)
    full_name    = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role         = Column(
        Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.reader,
    )
    is_active    = Column(String(10), nullable=False, default="true")
    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )
    last_login   = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    audit_logs   = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_workspace_id", "workspace_id"),
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User email={self.email} role={self.role}>"


# ── AuditLog ───────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable append-only record of every manual dashboard mutation.

    Never updated after insert. Deleting an audit log row is itself a violation
    that should be caught by DB-level insert-only policies in production.

    payload captures before/after state, e.g.:
        {"before": {"buying_stage": "Research"}, "after": {"buying_stage": "Negotiation"}}
    """
    __tablename__ = "audit_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    user_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action       = Column(String(100), nullable=False)   # e.g. "change_lead_stage"
    target_type  = Column(String(100), nullable=False)   # e.g. "customer", "memory"
    target_id    = Column(UUID(as_uuid=True), nullable=True)
    payload      = Column(JSONB, nullable=True)           # before/after diff
    ip_address   = Column(String(45), nullable=True)      # for compliance
    is_demo      = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # Relationship
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_workspace_id", "workspace_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action} target={self.target_type} "
            f"target_id={self.target_id}>"
        )


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

    One row per pipeline stage per message. Together they form the complete
    execution trace for that message — queryable for Event Replay.

    duration_ms is the wall-clock time for that stage only, enabling
    per-stage latency analysis.
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

    Phase 4: Written by Phase 5 (scheduling) and Phase 6 (follow-up).
    The dashboard reads this table to power the Queue Monitor panel.
    Currently a stub that Phase 5/6 will populate.
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
