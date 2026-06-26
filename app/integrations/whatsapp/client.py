"""
WhatsApp Business Cloud API client.

All outbound WhatsApp operations go through this module.
Retries up to 3 times on 5xx server errors before giving up.

Future integrations (Twilio, SMS, Email) each get their own
client in integrations/ — the pipeline calls the same interface.
"""

import asyncio
from typing import Optional

import httpx

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


async def send_text_message(to: str, body: str) -> Optional[str]:
    """
    Send a plain-text WhatsApp message via the Business Cloud API.

    Args:
        to:   Recipient phone number (digits only, no '+').
        body: Message text content.

    Returns:
        The WhatsApp message ID (wamid.xxx) on success, None on failure.
    """
    settings = get_settings()
    url = (
        f"{WHATSAPP_API_BASE}/{settings.whatsapp_api_version}"
        f"/{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    wa_message_id = (
                        data.get("messages", [{}])[0].get("id")
                    )
                    logger.info(
                        "whatsapp_message_sent",
                        to=to,
                        wa_message_id=wa_message_id,
                        attempt=attempt,
                    )
                    return wa_message_id

                elif response.status_code >= 500:
                    logger.warning(
                        "whatsapp_send_retry",
                        to=to,
                        status_code=response.status_code,
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                else:
                    # 4xx — do not retry, log and return
                    logger.error(
                        "whatsapp_send_failed",
                        to=to,
                        status_code=response.status_code,
                        response_body=response.text[:500],
                    )
                    return None

            except httpx.TimeoutException:
                logger.error(
                    "whatsapp_send_timeout",
                    to=to,
                    attempt=attempt,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

            except httpx.RequestError as exc:
                logger.error(
                    "whatsapp_request_error",
                    to=to,
                    error=str(exc),
                    attempt=attempt,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    logger.error(
        "whatsapp_send_exhausted_retries",
        to=to,
        max_retries=MAX_RETRIES,
    )
    return None
