import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class FrictionType(str, enum.Enum):
    LEAD_RESPONSE_DELAY  = "LEAD_RESPONSE_DELAY"
    MISSED_FOLLOWUP      = "MISSED_FOLLOWUP"
    SLA_VIOLATION        = "SLA_VIOLATION"
    APPROVAL_DELAY       = "APPROVAL_DELAY"
    WORKFLOW_STALL       = "WORKFLOW_STALL"
    OPPORTUNITY_LEAKAGE  = "OPPORTUNITY_LEAKAGE"
    CUSTOMER_INACTIVITY  = "CUSTOMER_INACTIVITY"
    DUPLICATE_WORK       = "DUPLICATE_WORK"


class FrictionSeverity(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class FrictionResolution(str, enum.Enum):
    OPEN         = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED     = "RESOLVED"


class WorkflowStageStatus(str, enum.Enum):
    NORMAL      = "NORMAL"
    WARNING     = "WARNING"
    BOTTLENECK  = "BOTTLENECK"
    CRITICAL    = "CRITICAL"


class SnapshotPeriod(str, enum.Enum):
    REALTIME = "realtime"
    HOURLY   = "hourly"
    DAILY    = "daily"


# ─── Models ───────────────────────────────────────────────────────────────────

class FrictionEvent(Base):
    """
    Persisted record of every detected friction instance.
    Each FrictionEvent contributes a score_contribution to the Business Friction Score.
    """
    __tablename__ = "friction_events"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id        = Column(UUID(as_uuid=True), nullable=False, index=True)

    friction_type       = Column(String(100), nullable=False, index=True)
    severity            = Column(String(50),  nullable=False, index=True)

    # Reference to the originating platform event or entity
    source_event_id     = Column(UUID(as_uuid=True), nullable=True)
    source_entity_type  = Column(String(50),  nullable=True)   # lead, approval, followup, workflow
    source_entity_id    = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Quantification
    score_contribution  = Column(Float, nullable=False, default=0.0)  # contribution to BFS (0–20)
    expected_value      = Column(Float, nullable=True)                 # expected metric value
    actual_value        = Column(Float, nullable=True)                 # actual metric value
    deviation_pct       = Column(Float, nullable=True)                 # % deviation from expected

    # Human-readable context
    description         = Column(String(2000), nullable=False)
    recommendation_hint = Column(String(1000), nullable=True)

    # Lifecycle
    resolution_status   = Column(String(50), nullable=False,
                                 default=FrictionResolution.OPEN.value, index=True)
    detected_at         = Column(DateTime(timezone=True),
                                 default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    resolved_at         = Column(DateTime(timezone=True), nullable=True)

    metadata_json       = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_friction_events_workspace_type", "workspace_id", "friction_type"),
        Index("ix_friction_events_workspace_severity", "workspace_id", "severity"),
    )


class SLAPolicy(Base):
    """
    Configurable SLA threshold per workspace.
    When an entity violates this SLA, a FrictionEvent is generated.
    """
    __tablename__ = "friction_sla_policies"

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id               = Column(UUID(as_uuid=True), nullable=False, index=True)

    policy_name                = Column(String(255), nullable=False)   # e.g. "New Lead Response"
    event_trigger              = Column(String(100), nullable=False)   # e.g. "lead.created"
    target_metric              = Column(String(100), nullable=False)   # e.g. "first_contact_minutes"
    description                = Column(String(500), nullable=True)

    warning_threshold_minutes  = Column(Integer, nullable=False)       # SLA warning level
    critical_threshold_minutes = Column(Integer, nullable=False)       # SLA breach level

    is_active                  = Column(Boolean, nullable=False, default=True)

    created_at                 = Column(DateTime(timezone=True),
                                        default=lambda: datetime.now(timezone.utc))
    updated_at                 = Column(DateTime(timezone=True),
                                        default=lambda: datetime.now(timezone.utc),
                                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_sla_policies_workspace", "workspace_id"),
    )


class FrictionScoreSnapshot(Base):
    """
    Time-series record of the Business Friction Score (0–100).
    Higher = more friction. Persisted on every recalculation.
    """
    __tablename__ = "friction_score_snapshots"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id    = Column(UUID(as_uuid=True), nullable=False, index=True)

    score           = Column(Float, nullable=False)          # 0–100
    previous_score  = Column(Float, nullable=True)
    score_delta     = Column(Float, nullable=True)           # positive = getting worse

    # JSON dict: {friction_type: contribution_value}
    contributors    = Column(JSON, nullable=False, default=dict)

    # Trend: IMPROVING / STABLE / DETERIORATING
    trend           = Column(String(50), nullable=False, default="STABLE")

    snapshot_period = Column(String(50), nullable=False,
                             default=SnapshotPeriod.REALTIME.value)
    calculated_at   = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("ix_friction_score_workspace_time", "workspace_id", "calculated_at"),
    )


class WorkflowStageLatency(Base):
    """
    Rolling average time per pipeline stage. Updated whenever a lead moves stages.
    Used by WorkflowBottleneckDetector to identify critical bottlenecks.
    """
    __tablename__ = "friction_workflow_latency"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id             = Column(UUID(as_uuid=True), nullable=False, index=True)

    stage_name               = Column(String(100), nullable=False)   # e.g. "Site Visit"
    expected_duration_hours  = Column(Float, nullable=False)          # configurable baseline
    actual_avg_hours         = Column(Float, nullable=False, default=0.0)
    sample_count             = Column(Integer, nullable=False, default=0)

    status                   = Column(String(50), nullable=False,
                                      default=WorkflowStageStatus.NORMAL.value)

    last_updated             = Column(DateTime(timezone=True),
                                      default=lambda: datetime.now(timezone.utc),
                                      onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_workflow_latency_workspace_stage", "workspace_id", "stage_name", unique=True),
    )
