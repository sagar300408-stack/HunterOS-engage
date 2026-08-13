from uuid import UUID


class OrchestrationError(Exception):
    """
    Base exception for Phase 3.5 orchestration failures.
    Raised when orchestration cannot proceed due to an illegal state,
    policy violation, or unrecoverable condition that is NOT an external I/O failure.
    """

    def __init__(self, message: str, action_id: UUID = None):
        self.action_id = action_id
        super().__init__(message)


class StalePinnedVersionError(OrchestrationError):
    """
    Raised when the Action's revision_id no longer matches the revision pinned
    at governance (Phase 3.4) time.

    This indicates that a concurrent mutation (e.g., a parallel status transition,
    evidence addition, or dependency change) has invalidated the orchestration window.
    Orchestration MUST NOT proceed when this is detected.
    """

    def __init__(
        self,
        action_id: UUID,
        pinned_revision_id: str,
        current_revision_id: str,
    ):
        self.action_id = action_id
        self.pinned_revision_id = pinned_revision_id
        self.current_revision_id = current_revision_id
        super().__init__(
            f"Action {action_id} revision has drifted: "
            f"pinned='{pinned_revision_id}' vs current='{current_revision_id}'. "
            "Concurrent mutation detected — orchestration aborted."
        )


class OrchestrationBlockedError(OrchestrationError):
    """
    Raised when one or more prerequisite Actions have reached a permanently
    failed terminal state (FAILED, CANCELLED, REJECTED, EXPIRED) and can
    never satisfy the dependency.

    This is distinct from a transient block (dependency still EXECUTING) —
    a blocked orchestration cannot be retried without human intervention.
    """

    def __init__(self, action_id: UUID, permanently_failed_dep_ids: list):
        self.action_id = action_id
        self.permanently_failed_dep_ids = permanently_failed_dep_ids
        dep_str = ", ".join(str(d) for d in permanently_failed_dep_ids)
        super().__init__(
            f"Action {action_id} has permanently-failed dependencies: [{dep_str}]. "
            "Orchestration cannot proceed — manual intervention required."
        )
