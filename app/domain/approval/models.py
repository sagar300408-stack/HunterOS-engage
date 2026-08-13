import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class ApprovalStageType(str, enum.Enum):
    SINGLE = "single"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)
    
    # Matching conditions format: [{"field": "risk", "operator": "==", "value": "HIGH"}, ...]
    matching_conditions = Column(JSON, nullable=False, default=list)
    
    # Stages format: [{"stage_index": 0, "type": "single", "approver_ids": ["admin"], "required_count": 1}]
    stages = Column(JSON, nullable=False, default=list)
    
    timeout_hours = Column(Integer, nullable=False, default=48)
    escalation_rule = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # The action that requires approval
    action_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action_version = Column(Integer, nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("approval_policies.id"), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    status = Column(String(50), nullable=False, default=ApprovalStatus.PENDING.value)
    current_stage_index = Column(Integer, nullable=False, default=0)
    
    requested_by = Column(String(100), nullable=False)
    
    # Snapshot of context when requested
    action_summary = Column(String(2000), nullable=True)
    business_context = Column(JSON, nullable=True)
    risk_level = Column(String(50), nullable=True)
    expected_impact = Column(String(2000), nullable=True)
    
    # Linking to Intelligence layer
    recommendation_id = Column(UUID(as_uuid=True), nullable=True)
    insight_id = Column(UUID(as_uuid=True), nullable=True)
    health_id = Column(UUID(as_uuid=True), nullable=True)
    
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    decision_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # SLA Tracking
    time_to_first_review_ms = Column(Integer, nullable=True)
    time_to_final_approval_ms = Column(Integer, nullable=True)
    sla_breached = Column(Boolean, nullable=False, default=False)
    escalation_triggered = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False, index=True)
    
    stage_index = Column(Integer, nullable=False)
    approver_id = Column(String(100), nullable=False)
    delegated_from_id = Column(String(100), nullable=True)
    
    decision = Column(String(50), nullable=False) # APPROVED or REJECTED
    comments = Column(String(2000), nullable=True)
    decision_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
