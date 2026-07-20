import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.domain.collaboration.models import (
    AutonomyLevel,
    RiskLevel,
    TaskStatus,
    ApprovalStatus,
    FeedbackRating,
    LearningRuleStatus
)

class ActionableIntentSchema(BaseModel):
    id: uuid.UUID
    intent_type: str
    context_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class DecisionExplanationSchema(BaseModel):
    reasoning_text: str
    confidence_factors: List[str]
    risk_factors: List[str]

    class Config:
        from_attributes = True

class DecisionAuditLogSchema(BaseModel):
    id: uuid.UUID
    policy_version: int
    execution_time_ms: float
    inputs_snapshot: Dict[str, Any]
    explanation: Optional[DecisionExplanationSchema]
    created_at: datetime

    class Config:
        from_attributes = True

class CollaborationTaskSchema(BaseModel):
    id: uuid.UUID
    intent: ActionableIntentSchema
    status: TaskStatus
    ownership: Optional[AutonomyLevel]
    risk_level: Optional[RiskLevel]
    confidence_score: Optional[float]
    assigned_to_agent_id: Optional[uuid.UUID]
    assigned_to_human_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    audit_log: Optional[DecisionAuditLogSchema]

    class Config:
        from_attributes = True

class AutonomyPolicySchema(BaseModel):
    id: uuid.UUID
    intent_type: str
    default_level: AutonomyLevel
    version: int

    class Config:
        from_attributes = True

class TaskApprovalChainSchema(BaseModel):
    id: uuid.UUID
    level: int
    required_role: Optional[str]
    approver_id: Optional[uuid.UUID]
    status: ApprovalStatus
    
    class Config:
        from_attributes = True

class LearningRuleSchema(BaseModel):
    id: uuid.UUID
    intent_type: str
    suggested_policy_change: Dict[str, Any]
    pattern_description: str
    occurrences: int
    status: LearningRuleStatus
    created_at: datetime

    class Config:
        from_attributes = True

# Request schemas for APIs
class PolicySimulationRequest(BaseModel):
    intent_type: str
    proposed_level: AutonomyLevel

class PolicySimulationResponse(BaseModel):
    expected_hours_saved: float
    expected_risk_increase_percent: float
    recommendation: str

class FeedbackRequest(BaseModel):
    task_id: uuid.UUID
    rating: FeedbackRating
    comments: Optional[str] = None
    is_override: bool = False
    override_details: Optional[Dict[str, Any]] = None

class ApprovalRequest(BaseModel):
    task_id: uuid.UUID
    approve: bool
    comments: Optional[str] = None
