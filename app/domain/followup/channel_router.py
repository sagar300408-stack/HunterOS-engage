from pydantic import BaseModel
from typing import Optional

class SendResult(BaseModel):
    success: bool
    provider_message_id: Optional[str]
    failure_reason: Optional[str]

async def send_message(channel: str, to: str, content: str) -> SendResult:
    # Stub: Normally we would call the WhatsApp / SMS API here.
    return SendResult(
        success=True,
        provider_message_id="stub_msg_123",
        failure_reason=None
    )
