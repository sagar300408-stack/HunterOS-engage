from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ApprovalContext(BaseModel):
    action_type: str
    target_system: str
    action_summary: Optional[str] = None
    business_context: Dict[str, Any] = {}
    risk_level: Optional[str] = None
    expected_impact: Optional[str] = None
    
    recommendation_id: Optional[UUID] = None
    insight_id: Optional[UUID] = None
    health_id: Optional[UUID] = None


class SubmitApprovalRequest(BaseModel):
    action_id: UUID
    context: ApprovalContext
    requested_by: str
    correlation_id: Optional[UUID] = None


class MakeDecisionRequest(BaseModel):
    approver_id: str
    decision: str  # APPROVED or REJECTED
    comments: Optional[str] = None
    delegated_from_id: Optional[str] = None


class ApprovalStageSchema(BaseModel):
    stage_index: int
    type: str
    approver_ids: List[str]
    required_count: int


class ApprovalPolicySchema(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    enabled: bool
    priority: int
    matching_conditions: List[Dict[str, Any]]
    stages: List[ApprovalStageSchema]
    timeout_hours: int
    escalation_rule: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ApprovalRequestResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    action_id: UUID
    policy_id: UUID
    correlation_id: Optional[UUID] = None
    
    status: str
    current_stage_index: int
    requested_by: str
    
    action_summary: Optional[str] = None
    business_context: Optional[Dict[str, Any]] = None
    risk_level: Optional[str] = None
    expected_impact: Optional[str] = None
    
    recommendation_id: Optional[UUID] = None
    insight_id: Optional[UUID] = None
    health_id: Optional[UUID] = None
    
    requested_at: datetime
    decision_deadline: Optional[datetime] = None
    
    time_to_first_review_ms: Optional[int] = None
    time_to_final_approval_ms: Optional[int] = None
    sla_breached: bool
    escalation_triggered: bool

    class Config:
        from_attributes = True
