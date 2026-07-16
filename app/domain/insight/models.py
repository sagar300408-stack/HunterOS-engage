import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class InsightCategory(str, enum.Enum):
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    PERFORMANCE_DECLINE = "performance_decline"
    OPERATIONAL_TREND = "operational_trend"
    CUSTOMER_BEHAVIOR = "customer_behavior"
    AUTOMATION_EFFECTIVENESS = "automation_effectiveness"
    SALES_ACTIVITY = "sales_activity"
    PIPELINE_MOVEMENT = "pipeline_movement"
    BUSINESS_OPPORTUNITY = "business_opportunity"
    BUSINESS_RISK = "business_risk"
    ANOMALY = "anomaly"


class InsightSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class InsightImpact(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InsightLifecycle(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class InsightSnapshot(Base):
    """
    Read model for Insight Engine.
    Represents an evidence-backed explanation of operational conditions.
    """
    __tablename__ = "insight_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Target entity
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Core Definition
    title = Column(String(255), nullable=False)
    summary = Column(String(1000), nullable=False)
    
    category = Column(String(50), nullable=False, index=True)
    severity = Column(String(50), nullable=False)
    impact = Column(String(50), nullable=False)
    
    # Lifecycle
    lifecycle_status = Column(String(50), nullable=False, default=InsightLifecycle.ACTIVE.value, index=True)
    
    # Extensibility and Proof
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0 based on evidence quality
    
    # Evidence Graph (nodes and edges)
    evidence_graph = Column(JSON, nullable=False, default=dict)
    graph_version = Column(String(50), nullable=False, default="1.0")
    
    # Legacy relational pointers for fast queries without parsing graph
    related_kpis = Column(JSON, nullable=False, default=list)
    related_health_objects = Column(JSON, nullable=False, default=list)
    related_timeline_events = Column(JSON, nullable=False, default=list)
    
    # Generator Metadata
    generator_name = Column(String(100), nullable=False, index=True)
    generator_version = Column(String(50), nullable=False)
    trigger_source = Column(String(100), nullable=False)
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
