from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/dev",
    tags=["Developer"]
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