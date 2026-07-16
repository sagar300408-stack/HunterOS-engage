import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.domain.conversations.models import Base


class HealthStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    EXCELLENT = "excellent"
    GOOD = "good"
    STABLE = "stable"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class HealthTrend(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    UNKNOWN = "unknown"


class HealthSnapshot(Base):
    """
    Read model for Operational Health Engine.
    Represents the operational condition of a specific business domain.
    """
    __tablename__ = "health_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Target entity
    target_type = Column(String(50), nullable=False, index=True)  # workspace, customer
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Core Definition
    health_name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    # Scores
    current_score = Column(Float, nullable=False)  # 0 to 100
    previous_score = Column(Float, nullable=True)
    
    # Interpretations
    trend = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)
    
    # Extensibility and Proof
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    evaluation_version = Column(String(50), nullable=False, default="1.0")
    
    # We use JSON for structured storage (sqlite compatibility via SQLAlchemy JSON)
    related_kpis = Column(JSON, nullable=False, default=list)
    supporting_evidence = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
