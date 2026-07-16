import enum
import uuid
from datetime import date

from sqlalchemy import Column, Integer, String, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

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
