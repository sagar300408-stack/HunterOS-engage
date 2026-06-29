# app/schemas/dev.py

from pydantic import BaseModel


class SimulateWhatsAppRequest(BaseModel):
    phone: str
    name: str
    message: str