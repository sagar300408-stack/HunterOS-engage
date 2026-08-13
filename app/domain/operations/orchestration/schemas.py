from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrchestrateActionRequest(BaseModel):
    """
    Request DTO for ActionOrchestrationEngine.orchestrate().
    """
    model_config = ConfigDict(frozen=True)

    pinned_action_version: int
    correlation_id: Optional[UUID] = None


class RetryOrchestrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: Optional[UUID] = None


class CancelOrchestrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: Optional[UUID] = None


class CompleteOrchestrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    outcome_data: Optional[str] = None
    correlation_id: Optional[UUID] = None


class FailOrchestrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    failure_type: str
    failure_reason: str
    retryable: bool
    correlation_id: Optional[UUID] = None


class TimeoutOrchestrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: Optional[UUID] = None


class OrchestrationAttemptDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: UUID
    run_id: UUID
    attempt_number: int
    state: str
    execution_handle: Optional[str] = None
    outcome: Optional[str] = None
    failure_type: Optional[str] = None
    failure_reason: Optional[str] = None
    retryable: Optional[bool] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class OrchestrationRunDTO(BaseModel):
    """
    API-serialisable projection of OrchestrationRun.
    """
    model_config = ConfigDict(frozen=True)

    id: UUID
    action_id: UUID
    workspace_id: UUID
    action_version: int
    state: str
    attempt_count: int
    max_attempts: int
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    attempts: List[OrchestrationAttemptDTO] = []

