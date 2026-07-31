class UnregisteredIntegrationError(Exception):
    """Raised when the Context Resolution Service encounters an integration type that has no registered resolver."""
    pass
