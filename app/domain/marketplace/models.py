import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class ConnectorCategory(str, enum.Enum):
    CRM = "CRM"
    EMAIL = "EMAIL"
    CALENDAR = "CALENDAR"
    COMMUNICATION = "COMMUNICATION"
    STORAGE = "STORAGE"
    ERP = "ERP"
    ACCOUNTING = "ACCOUNTING"
    MARKETING = "MARKETING"
    ANALYTICS = "ANALYTICS"
    CUSTOM = "CUSTOM"


class ConnectorCertification(str, enum.Enum):
    CERTIFIED = "CERTIFIED"
    EXPERIMENTAL = "EXPERIMENTAL"
    DEPRECATED = "DEPRECATED"
    INTERNAL = "INTERNAL"
    COMMUNITY = "COMMUNITY"


class ConnectorType(str, enum.Enum):
    NATIVE = "NATIVE"
    CUSTOM = "CUSTOM"
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class ConnectorStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    INACTIVE = "INACTIVE"


class InstallationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    PENDING_CONFIG = "PENDING_CONFIG"


class HealthLatencyBucket(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConnectorDefinition(Base):
    __tablename__ = "marketplace_connector_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # E.g. "salesforce", "hubspot"
    connector_id = Column(String(255), unique=True, nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    vendor = Column(String(255), nullable=False)
    
    category = Column(String(50), nullable=False)
    certification = Column(String(50), nullable=False)
    connector_type = Column(String(50), nullable=False, default=ConnectorType.EXTERNAL.value)
    status = Column(String(50), nullable=False, default=ConnectorStatus.ACTIVE.value)
    
    version = Column(String(50), nullable=False) # e.g. "1.2.0"
    supported_platform_versions = Column(String(255), nullable=False, default=">=1.0.0")
    
    icon_url = Column(String(1000), nullable=True)
    documentation_url = Column(String(1000), nullable=True)
    
    supported_capabilities = Column(JSON, nullable=False, default=list)
    required_credentials = Column(JSON, nullable=False, default=dict)
    configuration_schema = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class InstalledConnector(Base):
    __tablename__ = "marketplace_installed_connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Links to the Definition
    connector_id = Column(String(255), nullable=False, index=True)
    
    installation_version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default=InstallationStatus.PENDING_CONFIG.value)
    
    configuration = Column(JSON, nullable=False, default=dict)
    credential_reference = Column(String(255), nullable=True)
    
    enabled = Column(Boolean, nullable=False, default=False)
    
    last_synchronized_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ConnectorHealthRecord(Base):
    __tablename__ = "marketplace_connector_health_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_installed_connectors.id"), nullable=False, index=True)
    
    status = Column(String(50), nullable=False) # e.g. HEALTHY, DEGRADED, ERROR
    response_time_ms = Column(Integer, nullable=True)
    latency_bucket = Column(String(50), nullable=True)
    
    failure_count = Column(Integer, nullable=False, default=0)
    message = Column(String(2000), nullable=True)
    
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
