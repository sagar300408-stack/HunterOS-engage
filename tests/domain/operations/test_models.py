import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from app.domain.operations.models import Action, ActionType, ActionStatus, ActionPriority, ActionDependency

def test_action_model_invariants():
    workspace_id = uuid4()
    action = Action(
        workspace_id=workspace_id,
        action_type=ActionType.CREATE_TASK,
        target={"task_id": "123"}
    )
    assert action.status == ActionStatus.DETECTED
    assert action.priority == ActionPriority.NORMAL
    assert action.version_number == 1
    assert action.revision_id is not None
    assert action.id is not None
    assert action.created_at is not None
    assert action.updated_at is not None

def test_action_advance_revision():
    action = Action(workspace_id=uuid4(), action_type=ActionType.CREATE_TASK)
    old_rev = action.revision_id
    old_version = action.version_number
    
    action.advance_revision()
    
    assert action.revision_id != old_rev
    assert action.version_number == old_version + 1
