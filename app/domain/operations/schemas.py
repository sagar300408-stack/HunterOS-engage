from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.operations.models import ActionPriority, ActionStatus, ActionType
from app.domain.action.schemas import SubmitActionRequest
from app.domain.approval.schemas import ApprovalContext


class ActionEvidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_type: str
    content: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_source: str
    actor: Optional[str] = None
    timestamp: str
    context: Dict[str, Any] = Field(default_factory=dict)


class ActionDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    workspace_id: UUID
    action_type: ActionType
    status: ActionStatus
    priority: ActionPriority
    
    target: Dict[str, Any]
    owner: Dict[str, Any]
    source: Dict[str, Any]
    evidence: List[ActionEvidenceDTO]
    provenance: ActionProvenanceDTO
    execution_metadata: Dict[str, Any]

    idempotency_key: Optional[str] = None
    correlation_id: Optional[UUID] = None
    version_number: int
    revision_id: str
    created_at: str
    updated_at: str


class CreateActionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    action_type: ActionType
    priority: Optional[ActionPriority] = ActionPriority.NORMAL
    
    target: Dict[str, Any] = Field(default_factory=dict)
    owner: Dict[str, Any] = Field(default_factory=dict)
    source: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[ActionEvidenceDTO] = Field(default_factory=list)
    provenance: ActionProvenanceDTO
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)

    idempotency_key: Optional[str] = None
    correlation_id: Optional[UUID] = None
    dependency_action_ids: List[UUID] = Field(default_factory=list)


class TransitionActionStatusRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_status: ActionStatus
    reason: Optional[str] = None
    expected_revision_id: Optional[str] = None


class OperationalRequest(BaseModel):
    # What to do
    connector_id: str
    target_system: str
    action_type: str
    parameters: Dict[str, Any]
    idempotency_key: str
    
    # Metadata
    requested_by: str
    correlation_id: Optional[UUID] = None
    priority: str = "normal"
    
    # Governance Context
    approval_context: Optional[ApprovalContext] = None
    
    def to_submit_action_request(self) -> SubmitActionRequest:
        return SubmitActionRequest(
            connector_id=self.connector_id,
            target_system=self.target_system,
            action_type=self.action_type,
            parameters=self.parameters,
            idempotency_key=self.idempotency_key,
            correlation_id=self.correlation_id,
            priority=self.priority,
            requested_by=self.requested_by
        )
