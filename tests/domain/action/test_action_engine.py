import asyncio
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.action.engine import ActionEngine
from app.domain.action.models import ActionStatus, ActionPriority
from app.domain.action.schemas import SubmitActionRequest
from app.domain.integration.connectors.mocks import MockCRMConnector

# SQLAlchemy mapping requirements
from app.domain.action import models as action_models
from app.domain.integration import models as integration_models
from app.domain.briefing import models as briefing_models
from app.domain.recommendation import models as rec_models
from app.domain.insight import models as insight_models
from app.domain.health import models as health_models
from app.domain.kpi import models as kpi_models
from app.domain.conversations import models as conv_models
from app.domain.customers import models as cust_models
from app.domain.scheduling import models as sched_models
from app.domain.followup import models as followup_models
from app.domain.intent import models as intent_models
from app.domain.memory import models as memory_models

@pytest.mark.asyncio
async def test_submit_action_idempotency():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    mock_integration_engine = AsyncMock()
    
    engine = ActionEngine(mock_session, mock_event_bus, mock_integration_engine)
    
    workspace_id = uuid.uuid4()
    req = SubmitActionRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com", "first_name": "John", "last_name": "Doe"},
        idempotency_key="idemp_123",
        requested_by="test",
        is_orchestrated=True
    )
    
    # Mock existing action
    mock_existing = MagicMock()
    engine.action_repo.get_by_idempotency_key = AsyncMock(return_value=mock_existing)
    
    result = await engine.submit_action(workspace_id, req)
    
    assert result == mock_existing
    mock_event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_submit_action_and_execute():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    mock_integration_engine = AsyncMock()
    
    engine = ActionEngine(mock_session, mock_event_bus, mock_integration_engine)
    
    workspace_id = uuid.uuid4()
    req = SubmitActionRequest(
        connector_id="mock_crm_v1",
        target_system="crm",
        action_type="create_lead",
        parameters={"email": "test@test.com", "first_name": "John", "last_name": "Doe"},
        idempotency_key="idemp_123",
        requested_by="test",
        is_orchestrated=True
    )
    
    engine.action_repo.get_by_idempotency_key = AsyncMock(return_value=None)
    
    # Mock saving to DB to assign ID
    async def mock_save(action):
        action.id = uuid.uuid4()
        return action
        
    engine.action_repo.save_action = AsyncMock(side_effect=mock_save)
    engine.action_repo.update_action = AsyncMock(side_effect=lambda a: a)
    
    # Mock retrieval inside _execute
    async def mock_get_by_id(action_id):
        # We need to return an object that looks like the saved action
        action = action_models.ActionExecution(
            id=action_id,
            workspace_id=workspace_id,
            idempotency_key="idemp_123",
            connector_id="mock_crm_v1",
            target_system="crm",
            action_type="create_lead",
            parameters={"email": "test@test.com", "first_name": "John", "last_name": "Doe"},
            status=ActionStatus.PENDING.value,
            requested_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        )
        return action
        
    engine.action_repo.get_by_id = AsyncMock(side_effect=mock_get_by_id)
    
    # Mock the registry to return the CRM connector
    mock_registry = MagicMock()
    mock_registry.get_connector.return_value = MockCRMConnector()
    
    with patch("app.domain.action.engine.connector_registry", mock_registry):
        with patch("app.domain.action.tasks.execute_action_task.apply_async") as mock_celery:
            with patch("app.domain.action.engine.IntegrationRepository") as MockIntegRepo:
                mock_integ_repo = MockIntegRepo.return_value
                mock_integ_repo.get_active_connection_by_connector = AsyncMock(return_value=MagicMock())
                
                action = await engine.submit_action(workspace_id, req)
                
                assert action.status == ActionStatus.PENDING.value
                mock_celery.assert_called_once()
                
                # Now manually run _execute
                await engine._execute(action.id)
                
                # Verify update was called setting status to COMPLETED
                update_calls = engine.action_repo.update_action.call_args_list
                assert len(update_calls) == 3 # VALIDATING, EXECUTING, COMPLETED
                
                final_action = update_calls[-1][0][0]
                assert final_action.status == ActionStatus.COMPLETED.value
                assert final_action.execution_result["status"] == "success"
                
                # Verify events
                assert mock_event_bus.publish.call_count == 4 # submitted, validated, started, completed
