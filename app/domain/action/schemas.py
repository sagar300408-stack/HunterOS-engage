from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.action.models import ActionStatus, ActionPriority


class ExecutionResult(BaseModel):
    status: str
    execution_time_ms: int
    connector_response: Dict[str, Any] = {}
    external_reference_id: Optional[str] = None
    warnings: List[str] = []
    errors: List[str] = []
    is_retryable: bool = False


class SubmitActionRequest(BaseModel):
    connector_id: str
    target_system: str
    action_type: str
    parameters: Dict[str, Any]
    idempotency_key: str
    correlation_id: Optional[UUID] = None
    priority: str = ActionPriority.NORMAL.value
    requested_by: str
    is_orchestrated: bool = False


class ActionExecutionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    correlation_id: Optional[UUID] = None
    idempotency_key: str
    
    connector_id: str
    target_system: str
    
    action_type: str
    parameters: Dict[str, Any]
    
    status: str
    priority: str
    requested_by: str
    
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    queued_duration_ms: Optional[int] = None
    execution_duration_ms: Optional[int] = None
    total_duration_ms: Optional[int] = None
    
    execution_result: Optional[ExecutionResult] = None
    error_details: Optional[str] = None
    
    retry_count: int
    max_retries: int
    
    engine_version: str
    connector_version: Optional[str] = None

    class Config:
        from_attributes = True
