import httpx
from typing import Any, Dict

from app.utils.logger import get_logger
from app.integrations.whatsapp.config import WhatsAppConfig
from app.integrations.whatsapp.exceptions import APIError, AuthenticationError
from app.integrations.whatsapp.schemas import (
    OutgoingTemplateMessage,
    PhoneNumberInfoResponse,
    MessageResponse
)

logger = get_logger(__name__)

class WhatsAppClient:
    """Client for interacting directly with the Meta Graph API."""

    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.base_url = f"https://graph.facebook.com/{config.api_version}"
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Internal helper to execute HTTP requests with error handling."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method, 
                    url=url, 
                    headers=self.headers, 
                    timeout=10.0,
                    **kwargs
                )
            except httpx.RequestError as e:
                logger.error("whatsapp_client_network_error", error=str(e), url=url)
                raise APIError(f"Network error communicating with Meta API: {e}")

            if response.status_code == 401:
                logger.error("whatsapp_client_unauthorized", url=url)
                raise AuthenticationError("Unauthorized: Invalid or expired WhatsApp access token.")

            if not response.is_success:
                logger.error(
                    "whatsapp_client_api_error", 
                    status_code=response.status_code, 
                    response=response.text,
                    url=url
                )
                raise APIError(f"Meta API error ({response.status_code}): {response.text}")
                
            return response.json()

    async def verify_connection(self) -> PhoneNumberInfoResponse:
        """
        Verify the connection by fetching phone number information.
        
        GET /{phone_number_id}
        """
        endpoint = f"/{self.config.phone_number_id}"
        data = await self._request("GET", endpoint)
        return PhoneNumberInfoResponse(**data)

    async def send_template(self, payload: OutgoingTemplateMessage) -> MessageResponse:
        """
        Send a template message via the WhatsApp API.
        
        POST /{phone_number_id}/messages
        """
        endpoint = f"/{self.config.phone_number_id}/messages"
        data = await self._request("POST", endpoint, json=payload.model_dump(exclude_none=True))
        return MessageResponse(**data)
