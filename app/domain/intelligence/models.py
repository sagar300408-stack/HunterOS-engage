import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, JSON, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class IntelligenceSnapshotPeriod(str, enum.Enum):
    REALTIME = "realtime"
    HOURLY   = "hourly"
    DAILY    = "daily"


class OperationalHealthSnapshot(Base):
    """
    The master executive record holding the Four KPIs for a workspace.
    """
    __tablename__ = "intelligence_health_snapshots"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    # The 4 Executive KPIs (0-100)
    health_index          = Column(Float, nullable=False, default=100.0)
    friction_score        = Column(Float, nullable=False, default=0.0)
    risk_score            = Column(Float, nullable=False, default=0.0)
    leakage_score         = Column(Float, nullable=False, default=0.0)

    # Deltas from previous snapshot
    health_delta          = Column(Float, nullable=True)
    friction_delta        = Column(Float, nullable=True)
    risk_delta            = Column(Float, nullable=True)
    leakage_delta         = Column(Float, nullable=True)

    trend                 = Column(String(50), nullable=False, default="STABLE")

    snapshot_period       = Column(String(50), nullable=False, default=IntelligenceSnapshotPeriod.REALTIME.value)
    calculated_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("ix_intel_health_workspace_time", "workspace_id", "calculated_at"),
    )


class OpportunityLeakageEvent(Base):
    """
    Quantifies lost revenue due to dropped leads, ghosting, or stalled pipelines.
    """
    __tablename__ = "intelligence_leakage_events"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    leakage_type          = Column(String(100), nullable=False, index=True)  # e.g. "GHOSTED_CUSTOMER", "PROPOSAL_DELAYED"
    
    # Financial quantification
    revenue_at_risk       = Column(Float, nullable=False, default=0.0)       # e.g. ₹ 840,000
    currency              = Column(String(10), nullable=False, default="INR")
    
    source_entity_type    = Column(String(50), nullable=True)
    source_entity_id      = Column(UUID(as_uuid=True), nullable=True)

    description           = Column(String(2000), nullable=False)
    
    detected_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_recovered          = Column(Boolean, nullable=False, default=False)
    recovered_at          = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_intel_leakage_workspace", "workspace_id", "is_recovered"),
    )


class RootCauseAnalysis(Base):
    """
    Diagnostic connection explaining WHY a friction or leakage event happened.
    """
    __tablename__ = "intelligence_root_causes"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    # What problem is being explained?
    target_event_type     = Column(String(50), nullable=False)   # "friction" or "leakage"
    target_event_id       = Column(UUID(as_uuid=True), nullable=False)

    # The actual root cause
    cause_category        = Column(String(100), nullable=False)  # e.g., "CAPACITY_EXCEEDED", "PROCESS_BOTTLENECK"
    explanation           = Column(String(2000), nullable=False) # e.g., "Sales exec workload (64) exceeds capacity (35)"
    
    confidence_score      = Column(Float, nullable=False, default=0.8) # 0.0 - 1.0

    metadata_json         = Column(JSON, nullable=False, default=dict)
    analyzed_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class PredictionEvent(Base):
    """
    Forecast of future operational risks.
    """
    __tablename__ = "intelligence_predictions"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    prediction_type       = Column(String(100), nullable=False)  # e.g., "SLA_BREACH_FORECAST", "KPI_DETERIORATION"
    description           = Column(String(2000), nullable=False) # e.g., "Proposal delays will exceed SLA within 3 days"
    
    confidence_score      = Column(Float, nullable=False)        # e.g., 0.91 (91%)
    timeframe_days        = Column(Integer, nullable=False)      # e.g., 3

    predicted_impact      = Column(String(500), nullable=True)   # "Revenue at risk: 420k"
    
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    invalidated_at        = Column(DateTime(timezone=True), nullable=True)


class ExecutiveInsight(Base):
    """
    Human-readable business narrative generated from the other engines.
    """
    __tablename__ = "intelligence_executive_insights"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    insight_type          = Column(String(50), nullable=False)   # "WEEKLY_SUMMARY", "CRITICAL_ALERT", "ROOT_CAUSE_FINDING"
    narrative             = Column(String(4000), nullable=False) # The actual text a CEO would read

    priority              = Column(String(50), nullable=False, default="NORMAL")
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index("ix_intel_insights_workspace_time", "workspace_id", "created_at"),
    )


class ObservationDebounce(Base):
    """
    Simple table to track the last time a full pipeline scan was executed.
    Used by the ObservationEngine to enforce a 30-second cooldown.
    """
    __tablename__ = "intelligence_observation_debounce"

    workspace_id          = Column(UUID(as_uuid=True), primary_key=True)
    last_scan_at          = Column(DateTime(timezone=True), nullable=False)
    scan_count            = Column(Integer, nullable=False, default=0)
