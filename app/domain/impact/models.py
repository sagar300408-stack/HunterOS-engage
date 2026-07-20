import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Float, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.domain.conversations.models import Base

class ImpactCategory(str, enum.Enum):
    TIME_SAVINGS = "TIME_SAVINGS"
    PRODUCTIVITY = "PRODUCTIVITY"
    REVENUE_PROTECTION = "REVENUE_PROTECTION"
    COST_REDUCTION = "COST_REDUCTION"
    OPPORTUNITY_RECOVERY = "OPPORTUNITY_RECOVERY"
    STRATEGIC = "STRATEGIC"

class ReportFrequency(str, enum.Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ON_DEMAND = "ON_DEMAND"

class FinancialConfig(Base):
    __tablename__ = "impact_financial_configs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False, unique=True)
    average_hourly_cost = Column(Float, default=50.0)
    average_deal_value = Column(Float, default=10000.0)
    conversion_rate = Column(Float, default=0.10)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class BusinessTargets(Base):
    __tablename__ = "impact_business_targets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    kpi_name = Column(String, nullable=False) # e.g., "lead_response_minutes", "business_friction_score"
    target_value = Column(Float, nullable=False)
    condition = Column(String, default="<=") # <=, >=
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class BaselineMetrics(Base):
    __tablename__ = "impact_baseline_metrics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    metric_name = Column(String, nullable=False)
    baseline_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ImpactEvent(Base):
    __tablename__ = "impact_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    event_type = Column(String, nullable=False)
    source_feature = Column(String, nullable=False) # e.g., "CollaborationEngine", "Approvals"
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    attributions = relationship("ValueAttribution", back_populates="event")

class EvidenceTrace(Base):
    __tablename__ = "impact_evidence_traces"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attribution_id = Column(UUID(as_uuid=True), ForeignKey("impact_value_attributions.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    evidence_text = Column(String, nullable=False) # e.g., "Lead Recovered" -> "Meeting Scheduled"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    attribution = relationship("ValueAttribution", back_populates="evidence_traces")

class ValueAttribution(Base):
    __tablename__ = "impact_value_attributions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("impact_events.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    category = Column(SQLEnum(ImpactCategory), nullable=False)
    
    # Raw Operational Impact
    raw_metric_name = Column(String, nullable=True) # e.g., "minutes_saved"
    raw_metric_value = Column(Float, nullable=True)
    
    # Calculated Financial Impact
    estimated_financial_value = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    confidence_score = Column(Float, nullable=False) # 0.0 to 1.0
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    event = relationship("ImpactEvent", back_populates="attributions")
    evidence_traces = relationship("EvidenceTrace", back_populates="attribution")

class ExecutiveImpactReport(Base):
    __tablename__ = "impact_executive_reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    frequency = Column(SQLEnum(ReportFrequency), nullable=False)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    narrative_text = Column(String, nullable=False)
    data_snapshot = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
