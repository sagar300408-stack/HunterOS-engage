import pytest
from uuid import uuid4
from app.domain.operations.models import Action, ActionType, ActionStatus

class ActionEngine:
    def __init__(self, repo):
        self.repo = repo

    def process_action(self, action_id, workspace_id):
        action = self.repo.get_for_workspace(action_id, workspace_id)
        if not action:
            raise ValueError("Action not found")
        
        if action.status == ActionStatus.DETECTED:
            action.status = ActionStatus.PLANNED
            self.repo.save(action)
        return action

class MockRepo:
    def __init__(self):
        self.actions = {}
    
    def save(self, action):
        self.actions[action.id] = action
    
    def get_for_workspace(self, action_id, workspace_id):
        a = self.actions.get(action_id)
        return a if a and a.workspace_id == workspace_id else None

def test_engine_processes_action():
    repo = MockRepo()
    engine = ActionEngine(repo)
    
    ws_id = uuid4()
    action = Action(workspace_id=ws_id, action_type=ActionType.CREATE_TASK)
    repo.save(action)
    
    processed = engine.process_action(action.id, ws_id)
    assert processed.status == ActionStatus.PLANNED
