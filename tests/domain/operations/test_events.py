import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel

class UniversalBaseEvent(BaseModel):
    event_id: str
    workspace_id: str
    timestamp: datetime

class ActionCreatedEvent(UniversalBaseEvent):
    action_id: str
    action_type: str

class ActionStatusChangedEvent(UniversalBaseEvent):
    action_id: str
    old_status: str
    new_status: str

def test_action_created_event():
    event = ActionCreatedEvent(
        event_id=str(uuid4()),
        workspace_id=str(uuid4()),
        timestamp=datetime.utcnow(),
        action_id=str(uuid4()),
        action_type="CREATE_TASK"
    )
    assert event.event_id is not None
    assert event.action_type == "CREATE_TASK"
    assert isinstance(event, UniversalBaseEvent)

def test_action_status_changed_event():
    event = ActionStatusChangedEvent(
        event_id=str(uuid4()),
        workspace_id=str(uuid4()),
        timestamp=datetime.utcnow(),
        action_id=str(uuid4()),
        old_status="READY",
        new_status="EXECUTING"
    )
    assert event.old_status == "READY"
    assert event.new_status == "EXECUTING"
    assert isinstance(event, UniversalBaseEvent)
