class EventBusError(Exception):
    """Base exception for all Event Bus related errors."""
    pass


class EventValidationError(EventBusError):
    """Raised when an event fails validation before dispatch."""
    pass


class ConsumerRegistrationError(EventBusError):
    """Raised when there is an issue registering a consumer."""
    pass
