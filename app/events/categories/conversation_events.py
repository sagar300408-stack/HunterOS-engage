from pydantic import Field

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory


class ConversationEvent(UniversalBaseEvent):
    """
    Base event for all CONVERSATION category events.
    """
    category: EventCategory = Field(default=EventCategory.CONVERSATION, frozen=True)


class CustomerRepliedEvent(ConversationEvent):
    """
    Fired when a customer replies in a conversation.
    """
    event_name: str = Field(default="customer.replied", frozen=True)
    
    # Concrete fields for this specific event
    message_content: str
    channel: str = Field(default="whatsapp")
    wa_message_id: str
