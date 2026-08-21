import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.domain.operations.models import Action, ActionStatus
from app.domain.approval.models import ApprovalRequest, ApprovalStatus
from app.domain.operations.orchestration.models import OrchestrationRun, OrchestrationAttempt, OrchestrationRunState, OrchestrationAttemptState
from app.domain.action.models import ActionExecution, ActionStatus as ExecutionStatus
from app.domain.operations.query import OperationalQueryService
from app.domain.operations.exceptions import ActionNotFoundError
from app.domain.operations.schemas import ActionReadiness


@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_planning():
    return AsyncMock()

@pytest.fixture
def query_service(mock_session, mock_planning):
    return OperationalQueryService(mock_session, mock_planning)

@pytest.mark.asyncio
async def test_get_operational_context_action_not_found(query_service: OperationalQueryService, mock_session):
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(ActionNotFoundError):
        await query_service.get_operational_context(uuid.uuid4(), uuid.uuid4())

@pytest.mark.asyncio
async def test_get_operational_context_full_chain(query_service: OperationalQueryService, mock_session, mock_planning):
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    action = Action(
        id=action_id,
        workspace_id=workspace_id,
        action_type="test_action",
        status=ActionStatus.EXECUTING,
        priority="HIGH",
        target={"system": "test"},
        owner={"id": "user_1"},
        version_number=2,
        revision_id="rev_1"
    )
    
    approval = ApprovalRequest(
        workspace_id=workspace_id,
        action_id=action_id,
        action_version=2,
        status=ApprovalStatus.APPROVED.value,
        policy_id=uuid.uuid4(),
        requested_by="user_1"
    )
    
    run = OrchestrationRun(
        id=run_id,
        workspace_id=workspace_id,
        action_id=action_id,
        action_version=2,
        state=OrchestrationRunState.EXECUTING,
        attempt_count=1
    )
    
    attempt = OrchestrationAttempt(
        run_id=run.id,
        attempt_number=1,
        state=OrchestrationAttemptState.EXECUTING,
        execution_handle="ext_123"
    )
    
    execution = ActionExecution(
        workspace_id=workspace_id,
        idempotency_key=f"{run.id}:1",
        connector_id="test_conn",
        target_system="test",
        action_type="test_action",
        status=ExecutionStatus.EXECUTING.value,
        requested_by="system"
    )
    
    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if " actions" in stmt_str:
            mock_result.scalars.return_value.first.return_value = action
        elif " approval_requests" in stmt_str:
            mock_result.scalars.return_value.first.return_value = approval
        elif " orchestration_runs" in stmt_str:
            mock_result.scalars.return_value.first.return_value = run
        elif " orchestration_attempts" in stmt_str:
            mock_result.scalars.return_value.first.return_value = attempt
        elif " action_executions" in stmt_str:
            mock_result.scalars.return_value.first.return_value = execution
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result
        
    mock_session.execute = mock_execute
    
    # Return a real ActionReadiness object so Pydantic validation passes
    mock_planning.evaluate_readiness.return_value = ActionReadiness(
        action_id=action_id,
        action_version=2,
        state="READY",
        blockers=[],
        blocking_dependencies=[],
        pending_dependencies=[],
        satisfied_dependencies=[],
        evaluated_at=datetime.now(timezone.utc).isoformat()
    )
    
    context = await query_service.get_operational_context(workspace_id, action_id)
    
    assert context.action.action_id == action_id
    assert context.action.status == ActionStatus.EXECUTING
    
    assert context.readiness.state == "READY"
    
    assert context.governance.approval_required is True
    assert context.governance.approval_status == ApprovalStatus.APPROVED.value
    assert context.governance.stale_authorization is False
    
    assert context.orchestration.run_id == run.id
    assert context.orchestration.state == OrchestrationRunState.EXECUTING
    
    assert context.execution.execution_handle == "ext_123"
    assert context.execution.state == ExecutionStatus.EXECUTING.value
    assert not context.attention_signals


@pytest.mark.asyncio
async def test_stale_authorization_detection(query_service: OperationalQueryService, mock_session, mock_planning):
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    action = Action(
        id=action_id,
        workspace_id=workspace_id,
        action_type="test_action",
        status=ActionStatus.PLANNED,
        version_number=3,
        revision_id="rev_1"
    )
    
    approval = ApprovalRequest(
        workspace_id=workspace_id,
        action_id=action_id,
        action_version=2,
        status=ApprovalStatus.APPROVED.value,
        policy_id=uuid.uuid4(),
        requested_by="user_1"
    )
    
    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if " actions" in stmt_str:
            mock_result.scalars.return_value.first.return_value = action
        elif " approval_requests" in stmt_str:
            if "action_version" in stmt_str:
                mock_result.scalars.return_value.first.return_value = None
            else:
                mock_result.scalar.return_value = True
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result
        
    mock_session.execute = mock_execute
    
    mock_planning.evaluate_readiness.return_value = ActionReadiness(
        action_id=action_id,
        action_version=action.version_number,
        state="READY",
        blockers=[],
        blocking_dependencies=[],
        pending_dependencies=[],
        satisfied_dependencies=[],
        evaluated_at=datetime.now(timezone.utc).isoformat()
    )
    
    context = await query_service.get_operational_context(workspace_id, action_id)
    
    assert context.governance.stale_authorization is True
    assert context.governance.approval_status is None
    
    signals = [s.code for s in context.attention_signals]
    assert "STALE_AUTHORIZATION" in signals


@pytest.mark.asyncio
async def test_workspace_summary_aggregation(query_service: OperationalQueryService, mock_session):
    w1 = uuid.uuid4()
    
    mock_call_idx = {"count": 0}
    
    async def mock_execute(stmt):
        mock_result = MagicMock()
        
        # Determine the order of queries based on OperationalQueryService.get_workspace_operational_summary
        # 1. Active actions (status.in_)
        # 2. Blocked actions (dependencies)
        # 3. Pending approvals (approval_requests)
        # 4. Executing (orchestration_runs)
        # 5. Failed actions
        # 6. Completed actions
        
        mock_call_idx["count"] += 1
        idx = mock_call_idx["count"]
        
        if idx == 1:
            mock_result.scalar.return_value = 2 # active
        elif idx == 2:
            mock_result.scalar.return_value = 0 # blocked
        elif idx == 3:
            mock_result.scalar.return_value = 0 # pending
        elif idx == 4:
            mock_result.scalar.return_value = 0 # executing
        elif idx == 5:
            mock_result.scalar.return_value = 1 # failed
        elif idx == 6:
            mock_result.scalar.return_value = 1 # completed
        else:
            mock_result.scalar.return_value = 0
            
        return mock_result
        
    mock_session.execute = mock_execute
    
    summary = await query_service.get_workspace_operational_summary(w1)
    
    assert summary["ACTIVE_ACTIONS"] == 2
    assert summary["FAILED"] == 1
    assert summary["COMPLETED"] == 1
    assert summary["BLOCKED_ACTIONS"] == 0
