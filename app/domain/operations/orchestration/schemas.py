from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrchestrateActionRequest(BaseModel):
    """
    Request DTO for ActionOrchestrationEngine.orchestrate().

    pinned_revision_id must be captured from action.revision_id immediately
    after evaluate_governance() transitions the Action to APPROVED.
    Any revision drift between that moment and the orchestrate() call
    will trigger StalePinnedVersionError.
    """
    model_config = ConfigDict(frozen=True)

    pinned_revision_id: str
    correlation_id: Optional[UUID] = None


class OrchestrationResultDTO(BaseModel):
    """
    API-serialisable projection of OrchestrationResult.
    Returned by OperationsEngine.orchestrate_approved_action()
    and exposed via the POST …/orchestrate HTTP endpoint.
    """
    model_config = ConfigDict(frozen=True)

    action_id: UUID
    workspace_id: UUID
    status: str               # OrchestrationOutcome value (HANDED_OFF | BLOCKED | STALE | FAILED)
    execution_handle: Optional[str] = None
    reason: Optional[str] = None
    completed_at: str         # ISO-8601 UTC timestamp
