from abc import ABC, abstractmethod
from typing import Optional
from app.config import get_settings
from app.integrations.whatsapp.client import send_text_message as real_send_text_message

class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_text_message(self, to: str, body: str) -> Optional[str]:
        pass

class MetaWhatsAppProvider(WhatsAppProvider):
    async def send_text_message(self, to: str, body: str) -> Optional[str]:
        return await real_send_text_message(to, body)

class SimulatedWhatsAppProvider(WhatsAppProvider):
    async def send_text_message(self, to: str, body: str) -> Optional[str]:
        from app.developer_tools.service import simulation_state
        from app.utils.logger import get_logger
        import uuid
        
        logger = get_logger(__name__)
        
        # Check simulation status
        if simulation_state.whatsapp_status == "offline":
            logger.error("whatsapp_send_failed", detail="WhatsApp API is offline (Simulated)")
            return None
            
        dummy_id = f"wamid.{uuid.uuid4()}"
        logger.info("whatsapp_message_sent_mock", to=to, wa_message_id=dummy_id, body_preview=body[:50])
        return dummy_id

def get_whatsapp_provider() -> WhatsAppProvider:
    settings = get_settings()
    if settings.enable_developer_tools:
        from app.developer_tools.service import simulation_state
        if settings.whatsapp_access_token.startswith("dummy") or settings.whatsapp_access_token == "change-me" or simulation_state.mock_whatsapp:
            return SimulatedWhatsAppProvider()
    return MetaWhatsAppProvider()
