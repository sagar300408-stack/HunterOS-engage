import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Float, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base

class AutonomyLevel(str, enum.Enum):
    AI_OWNED = "ai_owned"
    HUMAN_REVIEW = "human_review"
    SHARED = "shared"
    HUMAN_OWNED = "human_owned"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class FeedbackRating(str, enum.Enum):
    HELPFUL = "helpful"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    NEEDS_IMPROVEMENT = "needs_improvement"


class ActionableIntent(Base):
    __tablename__ = "collaboration_intent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    intent_type = Column(String, nullable=False) # e.g. "schedule_meeting", "approve_discount"
    context_data = Column(JSONB, default=dict) # e.g. {"customer_id": "...", "deal_value": 50000}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tasks = relationship("CollaborationTask", back_populates="intent")


class CollaborationTask(Base):
    __tablename__ = "collaboration_task"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_intent.id"), nullable=False)
    
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    ownership = Column(Enum(AutonomyLevel), nullable=True) # Final decision
    risk_level = Column(Enum(RiskLevel), nullable=True)
    confidence_score = Column(Float, nullable=True)

    assigned_to_agent_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_to_human_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    intent = relationship("ActionableIntent", back_populates="tasks")
    approvals = relationship("TaskApprovalChain", back_populates="task")
    escalations = relationship("TaskEscalation", back_populates="task")
    audit_log = relationship("DecisionAuditLog", back_populates="task", uselist=False)
    feedback = relationship("TaskFeedback", back_populates="task", uselist=False)


class AutonomyPolicy(Base):
    __tablename__ = "collaboration_autonomy_policy"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    intent_type = Column(String, nullable=False) # e.g. "schedule_meeting"
    default_level = Column(Enum(AutonomyLevel), nullable=False)
    version = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TaskApprovalChain(Base):
    __tablename__ = "collaboration_task_approval"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_task.id"), nullable=False)
    level = Column(Integer, nullable=False) # 1, 2, 3 (for multi-level)
    required_role = Column(String, nullable=True) # e.g. "Sales Manager", "Finance"
    approver_id = Column(UUID(as_uuid=True), nullable=True) # Specific user
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("CollaborationTask", back_populates="approvals")


class DecisionAuditLog(Base):
    __tablename__ = "collaboration_decision_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_task.id"), nullable=False)
    policy_version = Column(Integer, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    
    inputs_snapshot = Column(JSONB, nullable=False) # Captures context, exception flags, risk score
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task = relationship("CollaborationTask", back_populates="audit_log")
    explanation = relationship("DecisionExplanation", back_populates="audit_log", uselist=False)


class DecisionExplanation(Base):
    __tablename__ = "collaboration_decision_explanation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_decision_audit.id"), nullable=False)
    reasoning_text = Column(Text, nullable=False)
    confidence_factors = Column(JSONB, default=list) # E.g. ["Sales Executive Available", "Project Open"]
    risk_factors = Column(JSONB, default=list) # E.g. ["Deal Value > 10M"]
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit_log = relationship("DecisionAuditLog", back_populates="explanation")


class TaskEscalation(Base):
    __tablename__ = "collaboration_task_escalation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_task.id"), nullable=False)
    reason = Column(String, nullable=False) # e.g. "SLA_BREACH", "NO_AGENTS_AVAILABLE"
    escalated_to_role = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task = relationship("CollaborationTask", back_populates="escalations")


class TaskFeedback(Base):
    __tablename__ = "collaboration_task_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("collaboration_task.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    rating = Column(Enum(FeedbackRating), nullable=False)
    comments = Column(Text, nullable=True)
    is_override = Column(Boolean, default=False)
    override_details = Column(JSONB, nullable=True) # What did the human change?
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task = relationship("CollaborationTask", back_populates="feedback")


class LearningRuleStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class LearningRule(Base):
    __tablename__ = "collaboration_learning_rule"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    intent_type = Column(String, nullable=False)
    suggested_policy_change = Column(JSONB, nullable=False)
    pattern_description = Column(Text, nullable=False) # e.g. "Luxury Projects -> Assign Sales Exec C"
    occurrences = Column(Integer, default=1)
    
    status = Column(Enum(LearningRuleStatus), default=LearningRuleStatus.DRAFT)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
