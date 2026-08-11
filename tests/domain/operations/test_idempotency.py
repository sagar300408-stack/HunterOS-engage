import pytest
from uuid import uuid4
from app.domain.operations.models import Action, ActionType

class ConflictError(Exception):
    pass

class IdempotencyStore:
    def __init__(self):
        self.actions = []

    def create_action(self, workspace_id, action_type, idempotency_key, payload):
        for action in self.actions:
            if action.workspace_id == workspace_id and action.idempotency_key == idempotency_key:
                if action.target == payload:
                    return action
                else:
                    raise ConflictError("Idempotency collision with different payload")
        
        new_action = Action(
            workspace_id=workspace_id,
            action_type=action_type,
            idempotency_key=idempotency_key,
            target=payload
        )
        self.actions.append(new_action)
        return new_action

def test_idempotency_same_payload():
    store = IdempotencyStore()
    ws_id = uuid4()
    key = "idem-key-1"
    payload = {"foo": "bar"}
    
    action1 = store.create_action(ws_id, ActionType.CREATE_TASK, key, payload)
    action2 = store.create_action(ws_id, ActionType.CREATE_TASK, key, payload)
    
    assert action1 is action2

def test_idempotency_different_payload():
    store = IdempotencyStore()
    ws_id = uuid4()
    key = "idem-key-1"
    
    store.create_action(ws_id, ActionType.CREATE_TASK, key, {"foo": "bar"})
    
    with pytest.raises(ConflictError):
        store.create_action(ws_id, ActionType.CREATE_TASK, key, {"foo": "baz"})

def test_idempotency_different_workspace():
    store = IdempotencyStore()
    key = "idem-key-1"
    payload = {"foo": "bar"}
    
    action1 = store.create_action(uuid4(), ActionType.CREATE_TASK, key, payload)
    action2 = store.create_action(uuid4(), ActionType.CREATE_TASK, key, payload)
    
    assert action1 is not action2
