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
    platform_admin = "Platform Admin"
    org_owner      = "Organization Owner"
    executive      = "Executive"
    ops_manager    = "Operations Manager"
    team_lead      = "Team Lead"
    employee       = "Employee"
    reader         = "Read Only User"
    service        = "Service Account"
    
    # Legacy roles mapped to new concepts for backwards compatibility
    founder = "Founder"
    admin   = "Admin"
    sales   = "Sales"
    support = "Support"


# ── User ───────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Core user account for the HunterOS Engage platform.
    """
    __tablename__ = "users"
    # To avoid breaking alembic or existing code that might query "users" table, 
    # we use the same table name. We extend the model.

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
    is_active    = Column(Boolean, nullable=False, default=True)
    mfa_enabled  = Column(Boolean, nullable=False, default=False)
    mfa_secret   = Column(String(255), nullable=True)
    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )
    last_login   = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    audit_logs   = relationship("AuditLog", back_populates="user")
    sessions     = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_workspace_id", "workspace_id"),
        Index("ix_users_email", "email"),
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return f"<User email={self.email} role={self.role}>"


# ── UserSession ────────────────────────────────────────────────────────────────

class UserSession(Base):
    """
    Active sessions for users. Used for token revocation and device tracking.
    """
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(512), nullable=False, unique=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    
    user = relationship("User", back_populates="sessions")


# ── AuditLog ───────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable append-only record of every manual platform mutation.
    """
    __tablename__ = "audit_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    user_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action       = Column(String(100), nullable=False)   # e.g. "change_lead_stage", "login", "export"
    target_type  = Column(String(100), nullable=False)   # e.g. "customer", "security_policy"
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
        {'extend_existing': True}
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action} target={self.target_type} "
            f"target_id={self.target_id}>"
        )


# ── SecurityPolicy ─────────────────────────────────────────────────────────────

class SecurityPolicy(Base):
    """
    Organization-level security policies (MFA enforcement, session limits).
    """
    __tablename__ = "security_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=DEFAULT_WORKSPACE_ID)
    
    # Policy settings
    require_mfa = Column(Boolean, nullable=False, default=False)
    password_min_length = Column(Integer, nullable=False, default=12)
    session_idle_timeout_minutes = Column(Integer, nullable=False, default=60)
    max_concurrent_sessions = Column(Integer, nullable=False, default=3)
    allowed_domains = Column(JSONB, nullable=True) # e.g. ["company.com"]
    ip_allowlist = Column(JSONB, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
