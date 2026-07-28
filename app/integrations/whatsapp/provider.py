from typing import Optional

from app.utils.logger import get_logger
from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.schemas import (
    OutgoingTemplateMessage,
    WhatsAppTemplate,
    WhatsAppLanguage,
    MessageResponse
)

logger = get_logger(__name__)

class WhatsAppProvider:
    """High-level provider for WhatsApp functionality."""

    def __init__(self, client: WhatsAppClient):
        self._client = client

    async def verify_connection(self) -> bool:
        """
        Verify that the WhatsApp Cloud API integration is configured properly
        and the API is accessible.
        """
        try:
            info = await self._client.verify_connection()
            logger.info(
                "whatsapp_connection_verified", 
                phone_number=info.display_phone_number,
                verified_name=info.verified_name
            )
            return True
        except Exception as e:
            logger.error("whatsapp_connection_failed", error=str(e))
            return False

    async def send_test_message(self, recipient: str) -> MessageResponse:
        """
        Sends the default Meta 'hello_world' template message to the recipient.
        
        Args:
            recipient: The phone number to send the message to (with country code).
        """
        # Meta API expects the recipient number without the '+' prefix.
        clean_recipient = recipient.replace("+", "").strip()
        
        payload = OutgoingTemplateMessage(
            to=clean_recipient,
            template=WhatsAppTemplate(
                name="hello_world",
                language=WhatsAppLanguage(code="en_US")
            )
        )
        
        logger.info("whatsapp_sending_test_message", recipient=clean_recipient)
        response = await self._client.send_template(payload)
        logger.info("whatsapp_test_message_sent", response=response.model_dump())
        
        return response
