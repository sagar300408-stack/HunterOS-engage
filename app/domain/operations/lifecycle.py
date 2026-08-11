from typing import Optional

from app.domain.operations.models import ActionStatus


class InvalidStateTransition(Exception):
    """Raised when an illegal action status transition is attempted."""

    def __init__(self, current_status: ActionStatus, target_status: ActionStatus, reason: Optional[str] = None):
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason
        super().__init__(
            f"Invalid action state transition from '{current_status.value}' to '{target_status.value}'"
            + (f": {reason}" if reason else ".")
        )


def validate_status_transition(current: ActionStatus, target: ActionStatus) -> None:
    """
    Strict state machine for ActionStatus transitions.
    Raises InvalidStateTransition if the transition is not permitted.
    """
    if current == target:
        return

    allowed_transitions = {
        ActionStatus.DETECTED: {
            ActionStatus.PLANNED,
            ActionStatus.REJECTED,
            ActionStatus.CANCELLED,
        },
        ActionStatus.PLANNED: {
            ActionStatus.PENDING_APPROVAL,
            ActionStatus.APPROVED,
            ActionStatus.CANCELLED,
        },
        ActionStatus.PENDING_APPROVAL: {
            ActionStatus.APPROVED,
            ActionStatus.REJECTED,
            ActionStatus.CANCELLED,
            ActionStatus.EXPIRED,
        },
        ActionStatus.APPROVED: {
            ActionStatus.READY,
            ActionStatus.CANCELLED,
        },
        ActionStatus.READY: {
            ActionStatus.EXECUTING,
            ActionStatus.CANCELLED,
            ActionStatus.EXPIRED,
        },
        ActionStatus.EXECUTING: {
            ActionStatus.COMPLETED,
            ActionStatus.FAILED,
            ActionStatus.CANCELLED,
        },
        ActionStatus.FAILED: {
            ActionStatus.READY,  # e.g., retry
            ActionStatus.CANCELLED,
        },
        # Terminal states: COMPLETED, REJECTED, CANCELLED, EXPIRED
        ActionStatus.COMPLETED: set(),
        ActionStatus.REJECTED: set(),
        ActionStatus.CANCELLED: set(),
        ActionStatus.EXPIRED: set(),
    }

    if target not in allowed_transitions.get(current, set()):
        raise InvalidStateTransition(
            current_status=current,
            target_status=target,
            reason=f"Transition from {current.value} to {target.value} is not permitted."
        )
