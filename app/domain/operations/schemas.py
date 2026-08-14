from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.operations.models import ActionPriority, ActionStatus, ActionType
from app.domain.action.schemas import SubmitActionRequest
from app.domain.approval.schemas import ApprovalContext


# ── Operational Integration DTOs (Phase 3.7) ────────────────────────────────

class ActionSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: UUID
    action_type: str
    status: str
    priority: str
    version: int
    created_at: str


class GovernanceSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_required: bool
    approval_status: Optional[str] = None
    approval_request_id: Optional[UUID] = None
    stale_authorization: bool


class OrchestrationSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: Optional[UUID] = None
    state: Optional[str] = None
    attempt_count: int = 0


class ExecutionSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_handle: Optional[str] = None
    state: Optional[str] = None
    failure_classification: Optional[str] = None
    retryable: Optional[bool] = None
    completed_at: Optional[str] = None


class AttentionSignalDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: str
    reason: str
    source: str


class ActionReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: UUID
    state: str  # "READY" or "BLOCKED"
    blockers: List[UUID]
    satisfied_dependencies: List[UUID]
    action_version: int
    evaluated_at: str


class OperationalContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    action: ActionSummaryDTO
    readiness: ActionReadiness
    governance: GovernanceSummaryDTO
    orchestration: OrchestrationSummaryDTO
    execution: ExecutionSummaryDTO
    attention_signals: List[AttentionSignalDTO]
    evaluated_at: str  # The timestamp when this cross-table context was evaluated.


# ── Action DTOs ────────────────────────────────────────────────────────────

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


