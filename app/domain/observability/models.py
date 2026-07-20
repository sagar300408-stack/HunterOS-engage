import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID


# ── Alert ──────────────────────────────────────────────────────────────────────

class AlertSeverity(str, enum.Enum):
    info     = "info"
    warning  = "warning"
    critical = "critical"
    fatal    = "fatal"

class AlertStatus(str, enum.Enum):
    active   = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"

class Alert(Base):
    """
    Abnormal behavior detected in Infrastructure, Application, or Business metrics.
    """
    __tablename__ = "observability_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False) # e.g. "infrastructure", "business", "ai"
    severity = Column(Enum(AlertSeverity, name="alertseverity"), nullable=False, default=AlertSeverity.warning)
    status = Column(Enum(AlertStatus, name="alertstatus"), nullable=False, default=AlertStatus.active)
    
    incident_id = Column(UUID(as_uuid=True), ForeignKey("observability_incidents.id", ondelete="SET NULL"), nullable=True)
    
    metadata_payload = Column(JSONB, nullable=True) # Trigger values, thresholds
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    incident = relationship("Incident", back_populates="alerts")
    
    __table_args__ = (
        Index("ix_alerts_workspace_id", "workspace_id"),
        Index("ix_alerts_status", "status"),
    )


# ── Incident ───────────────────────────────────────────────────────────────────

class IncidentStatus(str, enum.Enum):
    investigating = "investigating"
    identified    = "identified"
    monitoring    = "monitoring"
    resolved      = "resolved"

class Incident(Base):
    """
    Chronological reconstruction of multiple alerts into a timeline.
    """
    __tablename__ = "observability_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    
    title = Column(String(255), nullable=False)
    status = Column(Enum(IncidentStatus, name="incidentstatus"), nullable=False, default=IncidentStatus.investigating)
    severity = Column(Enum(AlertSeverity, name="alertseverity"), nullable=False, default=AlertSeverity.critical)
    
    root_cause = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    alerts = relationship("Alert", back_populates="incident")
    
    __table_args__ = (
        Index("ix_incidents_workspace_id", "workspace_id"),
        Index("ix_incidents_status", "status"),
    )


# ── MetricRecord ───────────────────────────────────────────────────────────────

class MetricRecord(Base):
    """
    Historical storage of business and AI metrics. 
    (Infrastructure metrics should ideally live in Prometheus, but this provides a fallback).
    """
    __tablename__ = "observability_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    
    metric_name = Column(String(100), nullable=False) # e.g. "business_friction_score", "ai_prompt_cost"
    metric_value = Column(Float, nullable=False)
    
    dimensions = Column(JSONB, nullable=True) # Labels, e.g. {"model": "gpt-4"}
    
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    
    __table_args__ = (
        Index("ix_metrics_workspace_id_name", "workspace_id", "metric_name"),
        Index("ix_metrics_timestamp", "timestamp"),
    )
