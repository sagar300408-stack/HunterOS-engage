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
    Raised when the Action's version no longer matches the version pinned
    in the OrchestrationRun.
    """

    def __init__(
        self,
        action_id: UUID,
        pinned_action_version: int,
        current_action_version: int,
    ):
        self.action_id = action_id
        self.pinned_action_version = pinned_action_version
        self.current_action_version = current_action_version
        super().__init__(
            f"Action {action_id} version has drifted: "
            f"pinned='{pinned_action_version}' vs current='{current_action_version}'. "
            "Concurrent mutation detected — orchestration aborted."
        )


class OrchestrationBlockedError(OrchestrationError):
    """
    Raised when one or more prerequisite Actions have reached a permanently
    failed terminal state (FAILED, CANCELLED, REJECTED, EXPIRED) and can
    never satisfy the dependency.
    """

    def __init__(self, action_id: UUID, permanently_failed_dep_ids: list):
        self.action_id = action_id
        self.permanently_failed_dep_ids = permanently_failed_dep_ids
        dep_str = ", ".join(str(d) for d in permanently_failed_dep_ids)
        super().__init__(
            f"Action {action_id} has permanently-failed dependencies: [{dep_str}]. "
            "Orchestration cannot proceed — manual intervention required."
        )


class RetryLimitExceededError(OrchestrationError):
    """
    Raised when a retry is requested but the OrchestrationRun has already
    reached its maximum allowed attempts.
    """

    def __init__(self, action_id: UUID, run_id: UUID, max_attempts: int):
        self.run_id = run_id
        super().__init__(
            f"Action {action_id} (Run {run_id}) has exceeded max attempts of {max_attempts}."
        )


class InvalidOrchestrationStateError(OrchestrationError):
    """
    Raised when an operation (like retry or cancel) is requested on a run
    that is in an invalid state for that operation.
    """

    def __init__(self, action_id: UUID, run_id: UUID, current_state: str, operation: str):
        self.run_id = run_id
        super().__init__(
            f"Cannot perform {operation} on Action {action_id} (Run {run_id}) in state {current_state}."
        )
