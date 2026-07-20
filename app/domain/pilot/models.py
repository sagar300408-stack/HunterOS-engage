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
    Integer,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID


# ── PilotDeployment ────────────────────────────────────────────────────────────

class PilotPhase(str, enum.Enum):
    discovery = "discovery"
    setup = "setup"
    training = "training"
    limited_rollout = "limited_rollout"
    full_pilot = "full_pilot"
    review = "review"
    completed = "completed"
    paused = "paused"

class PilotDeployment(Base):
    """
    Tracks the lifecycle of a Pilot Deployment for a customer workspace.
    """
    __tablename__ = "pilot_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)
    
    company_name = Column(String(255), nullable=False)
    executive_sponsor = Column(String(255), nullable=True)
    
    phase = Column(Enum(PilotPhase, name="pilotphase"), nullable=False, default=PilotPhase.discovery)
    
    target_start_date = Column(DateTime(timezone=True), nullable=True)
    target_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Pre-defined success criteria JSON (e.g., {"target_friction_reduction": 20})
    success_criteria = Column(JSONB, nullable=False, default=dict)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.utcnow())

    feedback = relationship("PilotFeedback", back_populates="pilot")
    metrics = relationship("PilotMetrics", back_populates="pilot")
    
    __table_args__ = (
        Index("ix_pilot_deployments_workspace_id", "workspace_id"),
    )


# ── PilotFeedback ──────────────────────────────────────────────────────────────

class FeedbackSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class PilotFeedback(Base):
    """
    Continuous feedback captured from pilot users or executives.
    """
    __tablename__ = "pilot_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    pilot_id = Column(UUID(as_uuid=True), ForeignKey("pilot_deployments.id", ondelete="CASCADE"), nullable=False)
    
    user_id = Column(UUID(as_uuid=True), nullable=True) # Optional, can be anonymous
    
    content = Column(Text, nullable=False)
    severity = Column(Enum(FeedbackSeverity, name="feedbackseverity"), nullable=False, default=FeedbackSeverity.medium)
    business_impact = Column(String(100), nullable=True) # e.g. "Blocks workflow X"
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())

    pilot = relationship("PilotDeployment", back_populates="feedback")
    
    __table_args__ = (
        Index("ix_pilot_feedback_pilot_id", "pilot_id"),
    )


# ── PilotMetrics ───────────────────────────────────────────────────────────────

class PilotMetrics(Base):
    """
    Adoption and ROI metrics captured during the pilot to prove success.
    """
    __tablename__ = "pilot_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    pilot_id = Column(UUID(as_uuid=True), ForeignKey("pilot_deployments.id", ondelete="CASCADE"), nullable=False)
    
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    
    baseline_friction_score = Column(Float, nullable=True)
    current_friction_score = Column(Float, nullable=True)
    
    weekly_active_users = Column(Integer, nullable=True)
    recommendation_acceptance_rate = Column(Float, nullable=True)
    
    additional_metrics = Column(JSONB, nullable=False, default=dict)

    pilot = relationship("PilotDeployment", back_populates="metrics")
    
    __table_args__ = (
        Index("ix_pilot_metrics_pilot_id", "pilot_id"),
    )
