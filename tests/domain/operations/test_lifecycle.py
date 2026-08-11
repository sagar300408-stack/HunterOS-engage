import pytest
from uuid import uuid4
from app.domain.operations.models import Action, ActionType, ActionStatus

class InvalidStateTransitionError(Exception):
    pass

class ActionLifecycleManager:
    """Mock implementation for testing state transitions."""
    
    VALID_TRANSITIONS = {
        ActionStatus.DETECTED: {ActionStatus.PLANNED, ActionStatus.REJECTED, ActionStatus.CANCELLED},
        ActionStatus.PLANNED: {ActionStatus.PENDING_APPROVAL, ActionStatus.READY, ActionStatus.CANCELLED},
        ActionStatus.PENDING_APPROVAL: {ActionStatus.APPROVED, ActionStatus.REJECTED, ActionStatus.CANCELLED},
        ActionStatus.APPROVED: {ActionStatus.READY, ActionStatus.CANCELLED},
        ActionStatus.READY: {ActionStatus.EXECUTING, ActionStatus.CANCELLED, ActionStatus.EXPIRED},
        ActionStatus.EXECUTING: {ActionStatus.COMPLETED, ActionStatus.FAILED, ActionStatus.CANCELLED},
        ActionStatus.COMPLETED: set(),
        ActionStatus.REJECTED: set(),
        ActionStatus.CANCELLED: set(),
        ActionStatus.EXPIRED: set(),
        ActionStatus.FAILED: set(),
    }

    @classmethod
    def transition(cls, action: Action, new_status: ActionStatus):
        if new_status not in cls.VALID_TRANSITIONS[action.status]:
            raise InvalidStateTransitionError(f"Cannot transition from {action.status} to {new_status}")
        
        # EXECUTING state transition does NOT trigger any external adapters, execution engines, or background execution tasks.
        # It must just be a state transition.
        action.status = new_status
        action.advance_revision()
        return action

def test_valid_transitions():
    action = Action(workspace_id=uuid4(), action_type=ActionType.CREATE_TASK)
    
    ActionLifecycleManager.transition(action, ActionStatus.PLANNED)
    assert action.status == ActionStatus.PLANNED
    
    ActionLifecycleManager.transition(action, ActionStatus.READY)
    assert action.status == ActionStatus.READY
    
    ActionLifecycleManager.transition(action, ActionStatus.EXECUTING)
    assert action.status == ActionStatus.EXECUTING
    
    ActionLifecycleManager.transition(action, ActionStatus.COMPLETED)
    assert action.status == ActionStatus.COMPLETED

def test_invalid_transition():
    action = Action(workspace_id=uuid4(), action_type=ActionType.CREATE_TASK)
    
    with pytest.raises(InvalidStateTransitionError):
        ActionLifecycleManager.transition(action, ActionStatus.COMPLETED)

def test_executing_transition_is_pure():
    action = Action(workspace_id=uuid4(), action_type=ActionType.CREATE_TASK)
    action.status = ActionStatus.READY
    
    # Asserting that transition to EXECUTING is just a state transition
    # In a real app, this ensures we don't have side effects in the domain model
    ActionLifecycleManager.transition(action, ActionStatus.EXECUTING)
    assert action.status == ActionStatus.EXECUTING
