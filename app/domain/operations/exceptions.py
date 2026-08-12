class ActionConflictError(Exception):
    """Raised when an action is created with an existing idempotency key but different properties."""
    pass

class ActionNotFoundError(Exception):
    """Raised when an action cannot be found."""
    pass

class DependencyCycleError(Exception):
    """Raised when adding a dependency would create a cycle."""
    pass

class WorkspaceIsolationError(Exception):
    """Raised when attempting to link actions across different workspaces."""
    pass

class InvalidDependencyError(Exception):
    """Raised when a dependency cannot be added or removed due to lifecycle constraints."""
    pass
