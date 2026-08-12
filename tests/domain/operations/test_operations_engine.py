import uuid
import pytest
from unittest.mock import AsyncMock

from app.domain.operations.engine import OperationsEngine
from app.domain.operations.schemas import OperationalRequest
from app.domain.approval.schemas import ApprovalContext

@pytest.mark.asyncio
async def test_operations_engine_evaluate_governance_requires_approval():
    mock_approval_engine = AsyncMock()
    mock_action_engine = AsyncMock()
    mock_repository = AsyncMock()
    
    engine = OperationsEngine(mock_approval_engine, mock_action_engine, repository=mock_repository)
    
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    mock_action = AsyncMock()
    mock_action.action_type = "create_lead"
    mock_action.target = "crm"
    mock_action.priority = "HIGH"
    mock_action.owner = "test_user"
    mock_action.revision_id = "1"
    mock_repository.get_action.return_value = mock_action
    
    engine.transition_status = AsyncMock()
    
    mock_approval = AsyncMock()
    mock_approval.id = uuid.uuid4()
    mock_approval_engine.evaluate_action.return_value = (True, mock_approval)
    
    result = await engine.evaluate_governance(workspace_id, action_id)
    
    assert result["status"] == "awaiting_approval"
    assert result["approval_id"] == mock_approval.id
    engine.transition_status.assert_called_once()
    call_args = engine.transition_status.call_args[0]
    assert call_args[2].target_status.value == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_operations_engine_evaluate_governance_no_approval_required():
    mock_approval_engine = AsyncMock()
    mock_action_engine = AsyncMock()
    mock_repository = AsyncMock()
    
    engine = OperationsEngine(mock_approval_engine, mock_action_engine, repository=mock_repository)
    
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    mock_action = AsyncMock()
    mock_action.action_type = "create_lead"
    mock_action.target = "crm"
    mock_action.priority = "LOW"
    mock_action.owner = "test_user"
    mock_action.revision_id = "1"
    mock_repository.get_action.return_value = mock_action
    
    engine.transition_status = AsyncMock()
    
    mock_approval_engine.evaluate_action.return_value = (False, None)
    
    result = await engine.evaluate_governance(workspace_id, action_id)
    
    assert result["status"] == "approved"
    engine.transition_status.assert_called_once()
    call_args = engine.transition_status.call_args[0]
    assert call_args[2].target_status.value == "APPROVED"
