"""
Tests for IntegrationExecutionPort
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.action.schemas import SubmitActionRequest
from app.domain.operations.orchestration.schemas import ExecutionCommand
from app.domain.operations.orchestration.integration_port import (
    IntegrationExecutionPort, CapabilityError
)
from app.domain.action.models import ActionExecution


@pytest.mark.asyncio
async def test_integration_port_resolves_and_submits():
    mock_action_engine = AsyncMock()
    port = IntegrationExecutionPort(mock_action_engine)
    
    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    
    command = ExecutionCommand(
        workspace_id=workspace_id,
        action_id=uuid.uuid4(),
        action_version=2,
        action_type="create_lead",
        target={"connector_id": "test_conn", "target_system": "test_sys"},
        parameters={"email": "test@test.com"},
        orchestration_run_id=run_id,
        orchestration_attempt_id=attempt_id,
        correlation_id=correlation_id
    )
    
    mock_execution = ActionExecution()
    mock_execution.id = uuid.uuid4()
    mock_action_engine.submit_action.return_value = mock_execution
    
    handle = await port.submit(command)
    
    assert handle == str(mock_execution.id)
    
    mock_action_engine.submit_action.assert_awaited_once()
    args, kwargs = mock_action_engine.submit_action.call_args
    req: SubmitActionRequest = args[1]
    
    assert req.connector_id == "test_conn"
    assert req.target_system == "test_sys"
    assert req.action_type == "create_lead"
    assert req.parameters == {"email": "test@test.com"}
    assert req.idempotency_key == f"{run_id}:{attempt_id}"
    assert req.correlation_id == correlation_id
    assert req.is_orchestrated is True

@pytest.mark.asyncio
async def test_integration_port_discovers_connector():
    mock_action_engine = AsyncMock()
    port = IntegrationExecutionPort(mock_action_engine)
    
    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    
    # Missing target
    command = ExecutionCommand(
        workspace_id=workspace_id,
        action_id=uuid.uuid4(),
        action_version=2,
        action_type="create_lead",
        target={},
        parameters={"email": "test@test.com"},
        orchestration_run_id=run_id,
        orchestration_attempt_id=attempt_id,
        correlation_id=None
    )
    
    mock_execution = ActionExecution()
    mock_execution.id = uuid.uuid4()
    mock_action_engine.submit_action.return_value = mock_execution
    
    # We rely on action_registry and connector_registry defaults
    # "create_lead" is supported by "crm" connector types.
    # To avoid relying on global state in tests, we patch the registries
    with patch("app.domain.operations.orchestration.integration_port.action_registry") as mock_ar, \
         patch("app.domain.operations.orchestration.integration_port.connector_registry") as mock_cr:
         
        mock_ar.get.return_value = True # mock definition
        
        mock_connector = AsyncMock()
        mock_connector.metadata.supported_actions = ["create_lead"]
        mock_connector.metadata.connector_id = "discovered_conn"
        mock_connector.metadata.connector_type = "discovered_sys"
        mock_cr.get_all_connectors.return_value = [mock_connector]
        
        handle = await port.submit(command)
        
    assert handle == str(mock_execution.id)
    args, kwargs = mock_action_engine.submit_action.call_args
    req: SubmitActionRequest = args[1]
    assert req.connector_id == "discovered_conn"
    assert req.target_system == "discovered_sys"
