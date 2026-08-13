import enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


class OrchestrationOutcome(str, enum.Enum):
    """Terminal outcomes for a single orchestration attempt."""
    HANDED_OFF = "HANDED_OFF"   # ExecutionPort.submit() returned successfully
    BLOCKED    = "BLOCKED"      # Permanently-failed dependency — cannot proceed
    STALE      = "STALE"        # revision_id drifted since governance approval
    FAILED     = "FAILED"       # Unexpected error during orchestration steps


@dataclass(frozen=True)
class OrchestrationPlan:
    """
    Immutable record capturing the orchestration intent at the moment
    governance (Phase 3.4) transitions the Action to APPROVED.

    The pinned_revision_id is the authoritative concurrency token:
    if the Action's revision_id diverges from this value by the time
    Phase 3.5 picks it up, orchestration MUST abort with StalePinnedVersionError.
    """
    action_id: UUID
    workspace_id: UUID
    pinned_revision_id: str        # action.revision_id immediately after APPROVED transition
    pinned_version_number: int     # action.version_number at that same moment
    created_at: datetime


@dataclass(frozen=True)
class OrchestrationResult:
    """
    Immutable result produced by ActionOrchestrationEngine.orchestrate().
    Stored in the caller for observability; not persisted as its own DB record.
    Key data points (e.g. execution_handle) ARE written into Action.execution_metadata.
    """
    action_id: UUID
    workspace_id: UUID
    status: OrchestrationOutcome
    execution_handle: Optional[str]     # Opaque handle returned by ExecutionPort (e.g. Celery task ID)
    reason: Optional[str]               # Human-readable explanation for non-HANDED_OFF outcomes
    completed_at: datetime


def now_utc() -> datetime:
    """Utility: current UTC timestamp with timezone info."""
    return datetime.now(timezone.utc)
