import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class RecommendationCategory(str, enum.Enum):
    SALES_OPTIMIZATION = "sales_optimization"
    CUSTOMER_ENGAGEMENT = "customer_engagement"
    FOLLOWUP_STRATEGY = "followup_strategy"
    PIPELINE_MANAGEMENT = "pipeline_management"
    AUTOMATION_OPTIMIZATION = "automation_optimization"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    BUSINESS_OPPORTUNITY = "business_opportunity"
    BUSINESS_RISK = "business_risk"
    PROCESS_IMPROVEMENT = "process_improvement"
    EXECUTIVE_ATTENTION = "executive_attention"


class ExpectedImpactCategory(str, enum.Enum):
    REVENUE = "revenue"
    CUSTOMER_ENGAGEMENT = "customer_engagement"
    PIPELINE = "pipeline"
    EFFICIENCY = "efficiency"
    AUTOMATION = "automation"
    RISK_REDUCTION = "risk_reduction"


class RecommendationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecommendationRisk(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationLifecycle(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class RecommendationSnapshot(Base):
    """
    Read model for Recommendation Engine.
    Represents an evidence-backed suggestion for a human decision maker.
    """
    __tablename__ = "recommendation_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Target entity
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Core Definition
    title = Column(String(255), nullable=False)
    summary = Column(String(2000), nullable=False)
    
    category = Column(String(50), nullable=False, index=True)
    expected_impact = Column(String(50), nullable=False) # ExpectedImpactCategory
    
    priority = Column(String(50), nullable=False)
    risk_level = Column(String(50), nullable=False)
    
    # Lifecycle
    lifecycle_status = Column(String(50), nullable=False, default=RecommendationLifecycle.ACTIVE.value, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extensibility and Proof
    recommendation_score = Column(Float, nullable=False, default=0.0) # 0.0 to 100.0 for sorting
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0 based on evidence quality
    
    # Structured Suggested Actions (List of dicts representing actionable steps)
    suggested_actions = Column(JSON, nullable=False, default=list)
    
    # Decision Trace (List of dicts or standard structure pointing to Insight, Health, KPI, Event)
    decision_trace = Column(JSON, nullable=False, default=dict)
    
    # Generator Metadata
    generator_name = Column(String(100), nullable=False, index=True)
    generator_version = Column(String(50), nullable=False)
    trigger_source = Column(String(100), nullable=False)
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
