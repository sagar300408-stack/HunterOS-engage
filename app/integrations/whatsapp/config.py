from dataclasses import dataclass
from app.config import get_settings
from app.integrations.whatsapp.exceptions import ConfigurationError

@dataclass
class WhatsAppConfig:
    access_token: str
    phone_number_id: str
    verify_token: str
    api_version: str

def get_whatsapp_config() -> WhatsAppConfig:
    """Extracts WhatsApp configuration from the main application settings."""
    settings = get_settings()
    
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise ConfigurationError("WhatsApp Cloud API configuration is missing or incomplete.")
        
    return WhatsAppConfig(
        access_token=settings.whatsapp_access_token,
        phone_number_id=settings.whatsapp_phone_number_id,
        verify_token=settings.whatsapp_verify_token,
        api_version=settings.whatsapp_api_version,
    )
