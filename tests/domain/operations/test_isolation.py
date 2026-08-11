import pytest
from uuid import uuid4
from app.domain.operations.models import Action, ActionType

class AccessDeniedError(Exception):
    pass

class ActionRepository:
    def __init__(self):
        self.actions = {}

    def save(self, action: Action):
        self.actions[action.id] = action

    def get_for_workspace(self, action_id, workspace_id):
        action = self.actions.get(action_id)
        if not action:
            return None
        if action.workspace_id != workspace_id:
            raise AccessDeniedError("Cross-workspace access denied")
        return action

def test_isolation_allowed():
    repo = ActionRepository()
    ws_id = uuid4()
    action = Action(workspace_id=ws_id, action_type=ActionType.CREATE_TASK)
    repo.save(action)
    
    retrieved = repo.get_for_workspace(action.id, ws_id)
    assert retrieved is action

def test_isolation_denied():
    repo = ActionRepository()
    ws_id1 = uuid4()
    ws_id2 = uuid4()
    action = Action(workspace_id=ws_id1, action_type=ActionType.CREATE_TASK)
    repo.save(action)
    
    with pytest.raises(AccessDeniedError):
        repo.get_for_workspace(action.id, ws_id2)
