import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class PlanStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    PLANNED = "PLANNED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"


class StepType(str, enum.Enum):
    WAIT = "WAIT"
    APPROVAL = "APPROVAL"
    ACTION = "ACTION"
    VALIDATION = "VALIDATION"
    DECISION = "DECISION"
    NOTIFICATION = "NOTIFICATION"
    CONDITION = "CONDITION"


class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class OperationalOpportunity(Base):
    __tablename__ = "autonomous_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    source = Column(String(50), nullable=False) # e.g. RECOMMENDATION, INSIGHT
    source_reference_id = Column(String(255), nullable=True)
    
    opportunity_type = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False, default="MEDIUM")
    risk_level = Column(String(50), nullable=False, default="LOW")
    
    business_objective = Column(String(1000), nullable=True)
    expected_impact = Column(String(1000), nullable=True)
    confidence = Column(Float, nullable=True)
    
    status = Column(String(50), nullable=False, default="NEW")
    correlation_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ExecutionPlan(Base):
    __tablename__ = "autonomous_execution_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("autonomous_opportunities.id"), nullable=False, index=True)
    
    plan_version = Column(String(50), nullable=False, default="1.0")
    status = Column(String(50), nullable=False, default=PlanStatus.PLANNED.value)
    
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    mission_priority = Column(Integer, nullable=False, default=0)
    
    compensation_plan = Column(JSON, nullable=True, default=dict)
    success_criteria = Column(JSON, nullable=True, default=dict)
    failure_strategy = Column(String(255), nullable=True) # e.g. COMPENSATE, ABORT, RETRY
    
    estimated_duration_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PlanStep(Base):
    __tablename__ = "autonomous_plan_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("autonomous_execution_plans.id"), nullable=False, index=True)
    
    step_index = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default=StepStatus.PENDING.value)
    
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    
    inputs = Column(JSON, nullable=False, default=dict)
    outputs = Column(JSON, nullable=False, default=dict)
    
    dependencies = Column(JSON, nullable=False, default=list) # Array of step indices
    
    retry_policy = Column(JSON, nullable=False, default=dict)
    timeout_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ExecutionJournal(Base):
    __tablename__ = "autonomous_execution_journals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("autonomous_execution_plans.id"), nullable=False, index=True)
    step_id = Column(UUID(as_uuid=True), ForeignKey("autonomous_plan_steps.id"), nullable=True, index=True)
    
    triggering_event = Column(String(255), nullable=True)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=False)
    reason = Column(String(2000), nullable=True)
    
    metadata_json = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
