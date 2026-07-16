import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class BriefingPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class BriefingSnapshot(Base):
    """
    Read model for Executive Briefing Engine.
    Represents a composed summary of operational intelligence for leadership.
    """
    __tablename__ = "briefing_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Template & Period
    template_name = Column(String(100), nullable=False, index=True)
    period = Column(String(50), nullable=False, index=True)
    
    # Core Briefing Sections
    executive_summary = Column(String(2000), nullable=False)
    
    # JSON Arrays holding summarized objects from previous intelligence layers
    kpi_summary = Column(JSON, nullable=False, default=list)
    health_summary = Column(JSON, nullable=False, default=list)
    key_insights = Column(JSON, nullable=False, default=list)
    priority_recommendations = Column(JSON, nullable=False, default=list)
    critical_risks = Column(JSON, nullable=False, default=list)
    business_opportunities = Column(JSON, nullable=False, default=list)
    
    # Extensibility and Proof
    supporting_references = Column(JSON, nullable=False, default=list) # List of UUIDs 
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0 based on average of sources
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
