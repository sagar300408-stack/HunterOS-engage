from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel


class OperationalOpportunitySchema(BaseModel):
    id: UUID
    workspace_id: UUID
    source: str
    source_reference_id: Optional[str] = None
    opportunity_type: str
    priority: str
    risk_level: str
    business_objective: Optional[str] = None
    expected_impact: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    correlation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanStepSchema(BaseModel):
    id: UUID
    plan_id: UUID
    step_index: int
    type: str
    status: str
    idempotency_key: Optional[str] = None
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    dependencies: List[int]
    retry_policy: Dict[str, Any]
    timeout_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionPlanSchema(BaseModel):
    id: UUID
    workspace_id: UUID
    opportunity_id: UUID
    plan_version: str
    status: str
    idempotency_key: Optional[str] = None
    mission_priority: int
    compensation_plan: Dict[str, Any]
    success_criteria: Dict[str, Any]
    failure_strategy: Optional[str] = None
    estimated_duration_ms: Optional[int] = None
    steps: Optional[List[PlanStepSchema]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionJournalSchema(BaseModel):
    id: UUID
    plan_id: UUID
    step_id: Optional[UUID] = None
    triggering_event: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: str
    reason: Optional[str] = None
    metadata_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutePlanRequest(BaseModel):
    idempotency_key: Optional[str] = None


class CancelPlanRequest(BaseModel):
    reason: str
