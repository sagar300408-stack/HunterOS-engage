import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.security.models import DEFAULT_WORKSPACE_ID


class LifecycleStage(str, enum.Enum):
    prospect = "prospect"
    pilot = "pilot"
    implementation = "implementation"
    adoption = "adoption"
    optimization = "optimization"
    renewal = "renewal"
    expansion = "expansion"

class CustomerLifecycle(Base):
    """
    Tracks the overarching lifecycle stage of a customer.
    """
    __tablename__ = "cs_customer_lifecycle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    current_stage = Column(Enum(LifecycleStage, name="lifecyclestage"), nullable=False, default=LifecycleStage.prospect)
    stage_entered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    
    csm_owner_id = Column(UUID(as_uuid=True), nullable=True) # HunterOS internal user
    
    renewal_date = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())


class PlaybookStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"

class SuccessPlaybook(Base):
    """
    A playbook triggered manually or automatically (e.g. 'Low Adoption Intervention').
    """
    __tablename__ = "cs_success_playbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    name = Column(String(255), nullable=False) # e.g., 'Low Adoption'
    trigger_reason = Column(String(255), nullable=True)
    
    status = Column(Enum(PlaybookStatus, name="playbookstatus"), nullable=False, default=PlaybookStatus.active)
    
    tasks_json = Column(JSONB, nullable=False, default=list) # Array of task states
    
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ExecutiveReview(Base):
    """
    Record of a Quarterly (or regular) Executive Business Review (EBR).
    """
    __tablename__ = "cs_executive_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    review_date = Column(DateTime(timezone=True), nullable=False)
    
    # Snapshot of ROI presented
    roi_snapshot_json = Column(JSONB, nullable=False, default=dict)
    
    executive_satisfaction = Column(String(50), nullable=True) # e.g. 'positive', 'neutral', 'negative'
    next_steps_json = Column(JSONB, nullable=False, default=list)


class SupportTicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"

class SupportTicket(Base):
    """
    Enterprise support ticketing, tied to SLA tracking.
    """
    __tablename__ = "cs_support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    subject = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    
    status = Column(Enum(SupportTicketStatus, name="supportticketstatus"), nullable=False, default=SupportTicketStatus.open)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    sla_breached = Column(Boolean, nullable=False, default=False)
