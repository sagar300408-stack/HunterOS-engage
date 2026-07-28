from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class WhatsAppLanguage(BaseModel):
    code: str = "en_US"

class WhatsAppTemplate(BaseModel):
    name: str
    language: WhatsAppLanguage = Field(default_factory=WhatsAppLanguage)

class OutgoingTemplateMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "template"
    template: WhatsAppTemplate

class PhoneNumberInfoResponse(BaseModel):
    verified_name: str
    display_phone_number: str
    id: str
    quality_rating: Optional[str] = None

class MessageResponseContact(BaseModel):
    input: str
    wa_id: str

class MessageResponseMessage(BaseModel):
    id: str
    message_status: Optional[str] = None

class MessageResponse(BaseModel):
    messaging_product: str
    contacts: List[MessageResponseContact]
    messages: List[MessageResponseMessage]
