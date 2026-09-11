from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.v1.security import verify_internal_network

router = APIRouter(
    prefix="/api/v1/dev",
    tags=["Developer"],
    dependencies=[Depends(verify_internal_network)]
)

class SimulateWhatsAppRequest(BaseModel):
    phone: str
    name: str
    message: str


@router.post("/simulate-whatsapp")
async def simulate_whatsapp(payload: SimulateWhatsAppRequest):
    return {
        "status": "received",
        "payload": payload
    }

class SendTestRequest(BaseModel):
    phone: str

def resolve_whatsapp_provider():
    from app.integrations.whatsapp.config import get_whatsapp_config
    from app.integrations.whatsapp.client import WhatsAppClient
    from app.integrations.whatsapp.provider import WhatsAppProvider
    wa_config = get_whatsapp_config()
    wa_client = WhatsAppClient(config=wa_config)
    return WhatsAppProvider(client=wa_client)

@router.post("/whatsapp/send-test", description="DEVELOPMENT ONLY: Send real WhatsApp test message")
async def send_test_whatsapp(
    request: SendTestRequest,
    whatsapp_provider = Depends(resolve_whatsapp_provider)
):
    """
    Temporary development endpoint.
    Performs a real API request to Meta's WhatsApp Cloud API.
    """
    response = await whatsapp_provider.send_test_message(request.phone)
    return response