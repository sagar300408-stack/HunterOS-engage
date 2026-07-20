import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID


class ConnectionStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    ERROR = "error"
    PENDING = "pending"


class IntegrationConnection(Base):
    """
    Core model for managing external system integrations in HunterOS.
    """
    __tablename__ = "integration_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Connector Identity
    connector_id = Column(String(100), nullable=False, index=True)      # e.g. mock_crm_v1
    connector_type = Column(String(50), nullable=False)                 # e.g. crm, email, slack
    provider = Column(String(100), nullable=False)                      # e.g. hubspot, mock_crm
    
    name = Column(String(255), nullable=False)                          # e.g. "Primary Sales CRM"
    status = Column(String(50), nullable=False, default=ConnectionStatus.PENDING.value)
    
    # Credentials (managed via CredentialProvider)
    credentials_json = Column(JSON, nullable=False, default=dict)
    
    # Configuration
    settings = Column(JSON, nullable=False, default=dict)
    webhook_secret = Column(String(255), nullable=True) # Used for validating incoming webhooks
    
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(2000), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    jobs = relationship("SyncJob", back_populates="integration")


# ── SyncJob ────────────────────────────────────────────────────────────────────

class SyncStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"

class SyncMode(str, enum.Enum):
    webhook = "webhook"       # Triggered by real-time event
    polling = "polling"       # Incremental poll
    batch = "batch"           # Full/Large historical pull
    on_demand = "on_demand"   # User clicked 'Sync Now'

class SyncJob(Base):
    """
    Tracks execution history for a synchronization event.
    """
    __tablename__ = "integration_sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False)
    
    mode = Column(Enum(SyncMode, name="syncmode"), nullable=False)
    status = Column(Enum(SyncStatus, name="syncstatus"), nullable=False, default=SyncStatus.running)
    
    records_processed = Column(Integer, nullable=False, default=0)
    records_failed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    integration = relationship("IntegrationConnection", back_populates="jobs")
    
    __table_args__ = (
        Index("ix_sync_jobs_integration_id", "integration_id"),
        Index("ix_sync_jobs_status", "status"),
    )
