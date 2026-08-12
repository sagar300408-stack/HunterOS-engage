from app.domain.operations.models import ActionStatus

class DependencySatisfactionPolicy:
    """Centralizes semantics for dependency satisfaction evaluation."""

    @staticmethod
    def is_satisfied(status: ActionStatus) -> bool:
        """A dependency is satisfied only when its prerequisite completes."""
        return status == ActionStatus.COMPLETED

    @staticmethod
    def is_permanently_failed(status: ActionStatus) -> bool:
        """A dependency is permanently unfulfillable if it reaches these terminal states."""
        return status in (
            ActionStatus.FAILED,
            ActionStatus.CANCELLED,
            ActionStatus.REJECTED,
            ActionStatus.EXPIRED
        )
