import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


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
    
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(2000), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
