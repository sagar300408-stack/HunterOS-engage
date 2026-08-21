import asyncio
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from app.domain.action.engine import ActionEngine
from app.domain.action.models import ActionStatus, ActionExecution
from app.domain.action.schemas import SubmitActionRequest
from app.domain.integration.models import IntegrationConnection
from app.domain.approval.schemas import GovernanceEvaluationResult

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_event_bus():
    return AsyncMock()

@pytest.fixture
def mock_integration_engine():
    engine = MagicMock()
    engine.cred_provider = MagicMock()
    engine.cred_provider.retrieve_credentials.return_value = {"api_key": "secret"}
    return engine

@pytest.fixture
def action_engine(mock_session, mock_event_bus, mock_integration_engine):
    engine = ActionEngine(mock_session, mock_event_bus, mock_integration_engine)
    
    # Mock save_action
    async def mock_save(action):
        if not action.id:
            action.id = uuid.uuid4()
        return action
    engine.action_repo.save_action = AsyncMock(side_effect=mock_save)
    engine.action_repo.update_action = AsyncMock(side_effect=lambda a: a)
    engine.action_repo.get_by_idempotency_key = AsyncMock(return_value=None)
    
    return engine

@pytest.mark.asyncio
async def test_r6_approval_gate_blocks_direct_execution(action_engine, mock_session):
    workspace_id = uuid.uuid4()
    req = SubmitActionRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com", "first_name": "John", "last_name": "Doe"},
        idempotency_key="idemp_123",
        requested_by="test",
        is_orchestrated=False # direct legacy submission
    )
    
    # Mock PolicyEvaluator to return approval_required=True
    with patch("app.domain.action.engine.ApprovalRepository") as MockAppRepo:
        mock_app_repo = MockAppRepo.return_value
        mock_app_repo.get_all_active_policies = AsyncMock(return_value=[])
        
        with patch("app.domain.action.engine.PolicyEvaluator.evaluate_policies") as mock_eval:
            mock_eval.return_value = GovernanceEvaluationResult(
                action_id=uuid.uuid4(),
                approval_required=True,
                reason="Policy requires approval",
                evaluated_at=datetime.now(timezone.utc),
                action_version=1,
                readiness_state="READY"
            )
            
            with pytest.raises(ValueError, match="requires approval and cannot be executed directly"):
                await action_engine.submit_action(workspace_id, req)

@pytest.mark.asyncio
async def test_r6_approval_gate_allows_orchestrated_execution(action_engine, mock_session):
    workspace_id = uuid.uuid4()
    req = SubmitActionRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com", "first_name": "John", "last_name": "Doe"},
        idempotency_key="idemp_123",
        requested_by="test",
        is_orchestrated=True # orchestrated, already approved
    )
    
    with patch("asyncio.create_task"):
        action = await action_engine.submit_action(workspace_id, req)
        assert action.status == ActionStatus.PENDING.value

@pytest.mark.asyncio
async def test_r5_connection_resolution_and_credentials(action_engine, mock_integration_engine):
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    action = ActionExecution(
        id=action_id,
        workspace_id=workspace_id,
        idempotency_key="idemp_123",
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com"},
        status=ActionStatus.PENDING.value,
        requested_at=datetime.now(timezone.utc)
    )
    action_engine.action_repo.get_by_id = AsyncMock(return_value=action)
    
    mock_connector = AsyncMock()
    mock_connector.metadata.version = "1.0"
    mock_connector.execute_action.return_value = {"success": True}
    
    mock_connection = IntegrationConnection(id=uuid.uuid4(), workspace_id=workspace_id)
    
    with patch("app.domain.action.engine.connector_registry.get_connector", return_value=mock_connector):
        with patch("app.domain.action.engine.IntegrationRepository") as MockIntegRepo:
            mock_integ_repo = MockIntegRepo.return_value
            mock_integ_repo.get_active_connection_by_connector = AsyncMock(return_value=mock_connection)
            
            await action_engine._execute(action_id)
            
            # Verify connection resolution
            mock_integ_repo.get_active_connection_by_connector.assert_called_once_with(workspace_id, "mock_crm_v1")
            
            # Verify credential retrieval
            mock_integration_engine.cred_provider.retrieve_credentials.assert_called_once_with(mock_connection)
            
            # Verify execution with real credentials
            mock_connector.execute_action.assert_called_once_with(
                "create_lead",
                {"email": "test@test.com"},
                credentials={"api_key": "secret"}
            )
            
            # Verify status update
            assert action.status == ActionStatus.COMPLETED.value
            assert action.execution_result["status"] == "success"

@pytest.mark.asyncio
async def test_r5_missing_connection_fails_safely(action_engine, mock_integration_engine):
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    action = ActionExecution(
        id=action_id,
        workspace_id=workspace_id,
        idempotency_key="idemp_123",
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com"},
        status=ActionStatus.PENDING.value,
        requested_at=datetime.now(timezone.utc)
    )
    action_engine.action_repo.get_by_id = AsyncMock(return_value=action)
    
    mock_connector = AsyncMock()
    mock_connector.metadata.version = "1.0"
    
    with patch("app.domain.action.engine.connector_registry.get_connector", return_value=mock_connector):
        with patch("app.domain.action.engine.IntegrationRepository") as MockIntegRepo:
            mock_integ_repo = MockIntegRepo.return_value
            # Return None to simulate missing or inactive connection
            mock_integ_repo.get_active_connection_by_connector = AsyncMock(return_value=None)
            
            await action_engine._execute(action_id)
            
            # Connector should NEVER be called
            mock_connector.execute_action.assert_not_called()
            
            # Action should be FAILED
            assert action.status == ActionStatus.FAILED.value
            assert "No active connection found" in action.error_details

@pytest.mark.asyncio
async def test_r5_missing_credentials_fails_safely(action_engine, mock_integration_engine):
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    action = ActionExecution(
        id=action_id,
        workspace_id=workspace_id,
        idempotency_key="idemp_123",
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com"},
        status=ActionStatus.PENDING.value,
        requested_at=datetime.now(timezone.utc)
    )
    action_engine.action_repo.get_by_id = AsyncMock(return_value=action)
    
    mock_connector = AsyncMock()
    mock_connector.metadata.version = "1.0"
    
    mock_connection = IntegrationConnection(id=uuid.uuid4(), workspace_id=workspace_id)
    
    # CredentialProvider returns empty credentials
    mock_integration_engine.cred_provider.retrieve_credentials.return_value = {}
    
    with patch("app.domain.action.engine.connector_registry.get_connector", return_value=mock_connector):
        with patch("app.domain.action.engine.IntegrationRepository") as MockIntegRepo:
            mock_integ_repo = MockIntegRepo.return_value
            mock_integ_repo.get_active_connection_by_connector = AsyncMock(return_value=mock_connection)
            
            await action_engine._execute(action_id)
            
            # Connector should NEVER be called
            mock_connector.execute_action.assert_not_called()
            
            # Action should be FAILED
            assert action.status == ActionStatus.FAILED.value
            assert "Credentials missing" in action.error_details
