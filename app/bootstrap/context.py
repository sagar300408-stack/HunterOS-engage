from app.application.context.service import ContextResolutionService
from app.events.model.integration_types import IntegrationType
from app.integrations.whatsapp.resolver import WhatsAppContextResolver

def bootstrap_context() -> ContextResolutionService:
    """
    Initializes the Application Context Resolution Layer.
    Registers all available integrations into the O(1) registry.
    """
    service = ContextResolutionService()
    
    # Register WhatsApp Resolver
    service.register(
        IntegrationType.WHATSAPP,
        WhatsAppContextResolver()
    )
    
    # Future integrations (e.g., INSTAGRAM, EMAIL, VOICE) will be registered here.

    return service
