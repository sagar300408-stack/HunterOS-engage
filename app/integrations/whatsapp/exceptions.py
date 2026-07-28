"""
Exceptions for the WhatsApp Cloud API integration.
"""

class WhatsAppError(Exception):
    """Base exception for all WhatsApp integration errors."""
    pass

class AuthenticationError(WhatsAppError):
    """Raised when authentication with the Meta API fails (e.g., invalid token)."""
    pass

class APIError(WhatsAppError):
    """Raised when the Meta API returns an error response."""
    pass

class ConfigurationError(WhatsAppError):
    """Raised when the WhatsApp integration is improperly configured."""
    pass
