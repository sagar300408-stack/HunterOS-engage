import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, UniqueConstraint, Index, Float, Boolean, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.domain.conversations.models import Base


class AnalyticsMetricType(str, enum.Enum):
    """
    Controlled enumeration of all allowable metric types to ensure data consistency.
    """
    LEADS_CREATED = "leads_created"
    QUALIFIED_LEADS = "qualified_leads"
    MEETINGS_SCHEDULED = "meetings_scheduled"
    MEETINGS_COMPLETED = "meetings_completed"
    CONVERSATIONS_STARTED = "conversations_started"
    CUSTOMER_REPLIES = "customer_replies"
    FOLLOWUPS_SCHEDULED = "followups_scheduled"
    FOLLOWUPS_COMPLETED = "followups_completed"
    AI_DECISIONS = "ai_decisions"


class AnalyticsDailyMetric(Base):
    """
    Read model for Analytics Projection. 
    Aggregates events into daily metric buckets for high-performance querying.
    """
    __tablename__ = "analytics_daily_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Generic target for the metric (e.g. 'workspace', 'customer', 'conversation')
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    metric_date = Column(Date, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    
    value = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'workspace_id', 'target_type', 'target_id', 'metric_date', 'metric_name',
            name='uix_analytics_daily_metric_target'
        ),
    )


# ── Product Analytics Models ───────────────────────────────────────────────────

class ProductUsageEvent(Base):
    """
    Granular product usage telemetry (logins, session duration, view loads).
    """
    __tablename__ = "analytics_product_usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    event_name = Column(String(100), nullable=False, index=True) # e.g. "login", "view_dashboard", "session_end"
    session_duration_seconds = Column(Integer, nullable=True)
    
    metadata_json = Column(JSONB, nullable=False, default=dict)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), index=True)

class FeatureAdoption(Base):
    """
    Aggregated records indicating whether an organization is actively using specific features.
    """
    __tablename__ = "analytics_feature_adoption"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    feature_name = Column(String(100), nullable=False, index=True) # e.g. "ai_recommendation", "friction_engine"
    is_adopted = Column(Boolean, nullable=False, default=False)
    
    first_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    total_uses = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        UniqueConstraint('workspace_id', 'feature_name', name='uix_feature_adoption_workspace'),
    )

class CustomerHealthSnapshot(Base):
    """
    Periodic snapshots of an organization's overall health score and engagement.
    """
    __tablename__ = "analytics_customer_health_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), index=True)
    
    health_score = Column(Float, nullable=False) # e.g. 0.0 to 100.0
    adoption_score = Column(Float, nullable=False)
    engagement_score = Column(Float, nullable=False)
    
    renewal_risk = Column(String(50), nullable=False, default="low") # low, medium, high
    
    metrics_json = Column(JSONB, nullable=False, default=dict)

class ProductExperiment(Base):
    """
    Records A/B tests or gradual rollouts, mapping users/workspaces to variant buckets.
    """
    __tablename__ = "analytics_product_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_name = Column(String(100), nullable=False, index=True)
    
    workspace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    variant = Column(String(50), nullable=False) # e.g. "control", "variant_a"
    
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    
    __table_args__ = (
        UniqueConstraint('experiment_name', 'workspace_id', 'user_id', name='uix_product_experiment_assignment'),
    )
