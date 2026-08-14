import pytest
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel

from app.domain.timeline.models import TimelineEntry, TimelineSeverity
from app.domain.timeline.strategies.operations import OperationalEventStrategy
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType

class DummyEvent(UniversalBaseEvent):
    action_id: uuid.UUID

def test_operational_event_strategy_extraction():
    strategy = OperationalEventStrategy(
        activity_type="action_created",
        title_template="Action created by {actor_id}",
        default_severity=TimelineSeverity.NORMAL
    )
    
    action_id = uuid.uuid4()
    event = DummyEvent(
        category=EventCategory.ACTION,
        event_name="action.created",
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.CUSTOMER,
        actor_id="user_123",
        source_subsystem="test",
        action_id=action_id,
        metadata={"reason": "Test reason"}
    )
    
    data = strategy.extract_structured_data(event)
    
    assert data["source_event_type"] == "action.created"
    assert data["action_id"] == str(action_id)
    assert data["actor_type"] == ActorType.CUSTOMER.value
    assert data["actor_id"] == "user_123"
    assert data["reason"] == "Test reason"

def test_operational_event_strategy_formatting():
    strategy = OperationalEventStrategy(
        activity_type="action_failed",
        title_template="Action failed for {action_id}",
        default_severity=TimelineSeverity.HIGH
    )
    
    data = {
        "source_event_type": "action.failed",
        "action_id": "act_123",
        "actor_id": "system",
        "failure_reason": "Network error"
    }
    
    formatted = strategy.format_for_display(data)
    
    assert formatted.title == "Action failed for act_123"
    assert "Network error" in formatted.description
    assert "action.failed" in formatted.description
