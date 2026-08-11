class ActionConflictError(Exception):
    """Raised when an action is created with an existing idempotency key but different properties."""
    pass

class ActionNotFoundError(Exception):
    """Raised when an action cannot be found."""
    pass
