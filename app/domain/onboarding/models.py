import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, Float, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base

class ProvisioningStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class IntegrationStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    SYNCING = "SYNCING"

class GoLiveStatus(str, enum.Enum):
    READY = "READY"
    READY_WITH_RECS = "READY_WITH_RECS"
    NOT_READY = "NOT_READY"

class WorkspaceProvisioning(Base):
    __tablename__ = "onboarding_workspace_provisioning"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False, unique=True)
    status = Column(SQLEnum(ProvisioningStatus), default=ProvisioningStatus.PENDING)
    current_step = Column(String, default="INITIALIZATION")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

class OnboardingIntegrationConnection(Base):
    __tablename__ = "onboarding_integrations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    provider_name = Column(String, nullable=False) # e.g., "SALESFORCE", "MOCK_CRM"
    status = Column(SQLEnum(IntegrationStatus), default=IntegrationStatus.DISCONNECTED)
    permissions_granted = Column(JSON, default=list)
    last_sync_at = Column(DateTime, nullable=True)
    health_score = Column(Float, default=1.0) # 0.0 to 1.0

class ImportJob(Base):
    __tablename__ = "onboarding_import_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_integrations.id"), nullable=True)
    entity_type = Column(String, nullable=False) # e.g., "CUSTOMER", "LEAD"
    status = Column(String, default="PENDING")
    rows_processed = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    data_quality_score = Column(Float, default=1.0) # 0.0 to 1.0 (from DataQualityEngine)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

class ValidationResult(Base):
    __tablename__ = "onboarding_validation_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    check_name = Column(String, nullable=False) # e.g., "MISSING_APPROVAL_POLICIES"
    status = Column(String, nullable=False) # "PASS", "FAIL", "WARNING"
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class GoLiveAssessment(Base):
    __tablename__ = "onboarding_golive_assessments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    status = Column(SQLEnum(GoLiveStatus), default=GoLiveStatus.NOT_READY)
    readiness_score = Column(Float, default=0.0)
    deployment_confidence = Column(Float, default=0.0)
    reason = Column(String, nullable=True)
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class OperationalCapabilityMatrix(Base):
    """
    Graceful degradation mapping. Tracks which features are autonomous vs manual.
    """
    __tablename__ = "onboarding_capability_matrix"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    capability_name = Column(String, nullable=False) # e.g., "LEAD_ASSIGNMENT"
    status = Column(String, default="AUTONOMOUS") # "AUTONOMOUS", "HUMAN_REVIEW", "LIMITED", "DISABLED"
    reason = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WorkspaceMaturity(Base):
    __tablename__ = "onboarding_workspace_maturity"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    level = Column(Integer, default=1) # 1: Connected, 2: Operational, 3: Intelligent, 4: Predictive, 5: Optimized
    score = Column(Float, default=0.0)
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
