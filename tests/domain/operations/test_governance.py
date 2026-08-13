import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.domain.operations.engine import OperationsEngine
from app.domain.operations.models import Action, ActionStatus, ActionPriority
from app.domain.operations.schemas import CreateActionRequest, ActionProvenanceDTO, TransitionActionStatusRequest
from app.domain.approval.engine import ApprovalEngine
from app.domain.approval.models import ApprovalRequest, ApprovalStatus
from app.domain.approval.schemas import MakeDecisionRequest
from app.domain.operations.exceptions import ActionNotFoundError


@pytest.fixture
def workspace_id():
    return uuid.uuid4()


@pytest.fixture
def mock_action_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_approval_engine():
    engine = AsyncMock()
    return engine


@pytest.fixture
def operations_engine(mock_approval_engine, mock_action_repo):
    engine = OperationsEngine(
        approval_engine=mock_approval_engine,
        action_engine=AsyncMock(),
        repository=mock_action_repo,
        planning_service=AsyncMock(),
        orchestration_engine=AsyncMock(),
        event_bus=AsyncMock()
    )
    return engine


@pytest.mark.asyncio
async def test_version_pinning_creates_approval_with_version(workspace_id, operations_engine, mock_action_repo, mock_approval_engine):
    # Setup Action
    action = Action(
        workspace_id=workspace_id,
        action_type="SEND_MESSAGE",
        version_number=5,
        status=ActionStatus.READY
    )
    mock_action_repo.get_action.return_value = action
    
    # Setup Approval Engine return
    mock_approval = MagicMock()
    mock_approval.id = uuid.uuid4()
    mock_approval_engine.evaluate_action.return_value = (True, mock_approval)
    
    # Execute
    res = await operations_engine.evaluate_governance(workspace_id, action.id)
    
    # Verify we passed action_version=5 to the ApprovalEngine
    assert res["status"] == "awaiting_approval"
    called_req = mock_approval_engine.evaluate_action.call_args[0][1]
    assert called_req.action_version == 5


@pytest.mark.asyncio
async def test_stale_approval_request_rejected(workspace_id, operations_engine, mock_action_repo, mock_approval_engine):
    # This tests the ApprovalEngine's process_decision directly if we want, but process_approval_decision
    # delegates to ApprovalEngine.process_decision. Let's mock ApprovalEngine throwing ValueError for staleness.
    mock_approval_engine.process_decision.side_effect = ValueError("Stale approval request")
    
    req = MakeDecisionRequest(approver_id="user1", decision="APPROVED")
    
    with pytest.raises(ValueError, match="Stale approval request"):
        await operations_engine.process_approval_decision(uuid.uuid4(), req, "user1")
        
    # Verify that action repo save was NOT called since it raised
    mock_action_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_atomic_transaction_rollback_on_failure(workspace_id, operations_engine, mock_action_repo, mock_approval_engine):
    # Simulate an approval that tries to transition the action, but transition fails
    mock_approval = MagicMock()
    mock_approval.id = uuid.uuid4()
    mock_approval.status = "approved"
    mock_approval.workspace_id = workspace_id
    mock_approval.action_id = uuid.uuid4()
    mock_approval_engine.process_decision.return_value = mock_approval
    
    # Simulate DB failure during transition_status
    mock_action_repo.get_action.side_effect = Exception("Database constraint failure")
    
    req = MakeDecisionRequest(approver_id="user1", decision="APPROVED")
    
    with pytest.raises(Exception, match="Database constraint failure"):
        await operations_engine.process_approval_decision(mock_approval.id, req, "user1")
        
    # The transaction must bubble the error up so the top-level session.commit() doesn't happen
    # Wait, save() is at the end of process_approval_decision. Let's ensure it wasn't called.
    mock_action_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_process_approval_decision_calls_save_for_single_commit(workspace_id, operations_engine, mock_action_repo, mock_approval_engine):
    # Simulate an intermediate stage approval (not final APPROVED or REJECTED)
    mock_approval = MagicMock()
    mock_approval.id = uuid.uuid4()
    mock_approval.status = "under_review"  # Not final
    mock_approval.workspace_id = workspace_id
    mock_approval.action_id = uuid.uuid4()
    mock_approval_engine.process_decision.return_value = mock_approval
    
    req = MakeDecisionRequest(approver_id="user1", decision="APPROVED")
    
    await operations_engine.process_approval_decision(mock_approval.id, req, "user1")
    
    # Ensure transition_status was NOT called
    mock_action_repo.get_action.assert_not_called()
    
    # Ensure single atomic commit is called at the end
    mock_action_repo.save.assert_called_once()
