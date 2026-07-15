import uuid
from pydantic import ValidationError
import pytest

from app.events.model.actor_types import ActorType
from app.events.categories.conversation_events import CustomerRepliedEvent


def test_customer_replied_event_valid():
    """Test that a valid concrete event is properly instantiated."""
    workspace_id = uuid.uuid4()
    
    event = CustomerRepliedEvent(
        workspace_id=workspace_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="conversation_engine",
        message_content="Hello, I need help.",
        wa_message_id="wamid.123456789"
    )
    
    assert event.workspace_id == workspace_id
    assert event.actor_type == ActorType.CUSTOMER
    assert event.source_subsystem == "conversation_engine"
    assert event.message_content == "Hello, I need help."
    assert event.wa_message_id == "wamid.123456789"
    assert event.channel == "whatsapp"
    assert event.event_name == "customer.replied"
    assert event.category.value == "CONVERSATION"
    assert event.event_id is not None
    assert event.occurred_at is not None

def test_missing_required_fields():
    """Test that missing fields raise a ValidationError."""
    with pytest.raises(ValidationError):
        # Missing workspace_id, actor_type, source_subsystem, etc.
        CustomerRepliedEvent(
            message_content="Hello",
            wa_message_id="wamid.123"
        )
