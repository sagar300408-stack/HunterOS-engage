import uuid
import pytest
from unittest.mock import AsyncMock

from app.domain.operations.engine import OperationsEngine
from app.domain.operations.schemas import OperationalRequest
from app.domain.approval.schemas import ApprovalContext

@pytest.mark.asyncio
async def test_operations_engine_submit_requires_approval():
    mock_approval_engine = AsyncMock()
    mock_action_engine = AsyncMock()
    
    engine = OperationsEngine(mock_approval_engine, mock_action_engine)
    
    workspace_id = uuid.uuid4()
    req = OperationalRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com"},
        idempotency_key="idemp_123",
        requested_by="test",
        approval_context=ApprovalContext(
            action_type="create_lead",
            target_system="crm",
            risk_level="HIGH"
        )
    )
    
    mock_approval = AsyncMock()
    mock_approval.id = uuid.uuid4()
    mock_approval_engine.evaluate_action.return_value = (True, mock_approval)
    
    result = await engine.submit_request(workspace_id, req)
    
    assert result["status"] == "awaiting_approval"
    mock_action_engine.submit_action.assert_not_called()


@pytest.mark.asyncio
async def test_operations_engine_submit_no_approval_required():
    mock_approval_engine = AsyncMock()
    mock_action_engine = AsyncMock()
    
    engine = OperationsEngine(mock_approval_engine, mock_action_engine)
    
    workspace_id = uuid.uuid4()
    req = OperationalRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com"},
        idempotency_key="idemp_123",
        requested_by="test",
        approval_context=ApprovalContext(
            action_type="create_lead",
            target_system="crm",
            risk_level="LOW"
        )
    )
    
    mock_approval_engine.evaluate_action.return_value = (False, None)
    
    mock_action = AsyncMock()
    mock_action.id = uuid.uuid4()
    mock_action_engine.submit_action.return_value = mock_action
    
    result = await engine.submit_request(workspace_id, req)
    
    assert result["status"] == "executing"
    mock_action_engine.submit_action.assert_called_once()
