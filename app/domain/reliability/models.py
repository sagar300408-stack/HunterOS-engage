import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    Float,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID


# ── PerformanceBenchmark ────────────────────────────────────────────────────────

class PerformanceBenchmark(Base):
    """
    Stores historical records of SLO compliance and benchmark runs.
    """
    __tablename__ = "reliability_benchmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    
    benchmark_name = Column(String(255), nullable=False) # e.g., "API_P99_Latency", "Dashboard_Load_Time"
    target_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    
    passed = Column(Boolean, nullable=False)
    
    metadata_payload = Column(JSONB, nullable=True) # test conditions, concurrency
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())

    __table_args__ = (
        Index("ix_reliability_benchmarks_timestamp", "timestamp"),
    )


# ── ReliabilityEvent ────────────────────────────────────────────────────────────

class EventType(str, enum.Enum):
    failover = "failover"
    degradation = "degradation"
    recovery = "recovery"
    chaos_experiment = "chaos_experiment"

class ReliabilityEvent(Base):
    """
    Tracks architectural degradation, failovers, and recovery events.
    """
    __tablename__ = "reliability_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    
    event_type = Column(Enum(EventType, name="reliabilityeventtype"), nullable=False)
    service_name = Column(String(100), nullable=False) # e.g., "CRM_Sync", "Primary_DB"
    description = Column(Text, nullable=True)
    
    resolved = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_reliability_events_service", "service_name"),
    )


# ── DeploymentRecord ────────────────────────────────────────────────────────────

class DeploymentStatus(str, enum.Enum):
    in_progress = "in_progress"
    success = "success"
    failed = "failed"
    rolled_back = "rolled_back"

class DeploymentRecord(Base):
    """
    Tracks deployments and rollout status.
    """
    __tablename__ = "reliability_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    
    version = Column(String(50), nullable=False)
    status = Column(Enum(DeploymentStatus, name="deploymentstatus"), nullable=False, default=DeploymentStatus.in_progress)
    
    rollback_version = Column(String(50), nullable=True)
    health_checks_passed = Column(Boolean, nullable=False, default=False)
    
    deployed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_reliability_deployments_version", "version"),
    )
