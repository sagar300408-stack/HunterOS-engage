import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.integration.engine import IntegrationEngine
from app.domain.integration.connectors.mocks import MockCRMConnector
from app.domain.integration.models import ConnectionStatus, IntegrationConnection
from app.domain.integration.credentials import JsonCredentialProvider

# SQLAlchemy mapping requirements
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
async def test_integration_engine_connect_valid():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    mock_registry = MagicMock()
    mock_registry.get_connector.return_value = MockCRMConnector()
    
    mock_event_bus = AsyncMock()
    
    engine = IntegrationEngine(mock_session, cred_provider=JsonCredentialProvider(), event_bus=mock_event_bus)
    
    async def mock_save(connection):
        # assign an ID just like DB would
        connection.id = uuid.uuid4()
        return connection
    engine.integration_repo.save_connection = AsyncMock(side_effect=mock_save)
    
    with patch("app.domain.integration.engine.connector_registry", mock_registry):
        credentials = {"api_key": "valid_key"}
        connection = await engine.connect_provider(
            workspace_id=workspace_id,
            connector_id="mock_crm_v1",
            name="My CRM",
            credentials=credentials,
            settings={}
        )
        
        # Verify status is connected because we sent valid_key
        assert connection.status == ConnectionStatus.CONNECTED.value
        assert connection.error_message is None
        
        # Verify provider set correctly
        assert connection.credentials_json == credentials
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event_called = mock_event_bus.publish.call_args[0][0]
        assert event_called.event_name == "integration.connected"
        assert event_called.metadata["status"] == ConnectionStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_integration_engine_connect_degraded():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    mock_registry = MagicMock()
    mock_registry.get_connector.return_value = MockCRMConnector()
    
    mock_event_bus = AsyncMock()
    
    engine = IntegrationEngine(mock_session, cred_provider=JsonCredentialProvider(), event_bus=mock_event_bus)
    
    async def mock_save(connection):
        connection.id = uuid.uuid4()
        return connection
    engine.integration_repo.save_connection = AsyncMock(side_effect=mock_save)
    
    with patch("app.domain.integration.engine.connector_registry", mock_registry):
        credentials = {"api_key": "degraded_key"}
        connection = await engine.connect_provider(
            workspace_id=workspace_id,
            connector_id="mock_crm_v1",
            name="My CRM",
            credentials=credentials,
            settings={}
        )
        
        # Verify status is degraded
        assert connection.status == ConnectionStatus.DEGRADED.value
        assert connection.error_message == "API rate limits nearing capacity."
        
        # Verify event was published as connected (degraded is a form of connected)
        mock_event_bus.publish.assert_called_once()
        event_called = mock_event_bus.publish.call_args[0][0]
        assert event_called.event_name == "integration.connected"
        assert event_called.metadata["status"] == ConnectionStatus.DEGRADED.value


@pytest.mark.asyncio
async def test_integration_engine_disconnect():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    conn_id = uuid.uuid4()
    
    mock_event_bus = AsyncMock()
    engine = IntegrationEngine(mock_session, cred_provider=JsonCredentialProvider(), event_bus=mock_event_bus)
    
    mock_conn = IntegrationConnection(
        id=conn_id,
        workspace_id=workspace_id,
        credentials_json={"api_key": "something"}
    )
    
    engine.integration_repo.get_connection = AsyncMock(return_value=mock_conn)
    engine.integration_repo.update_connection_status = AsyncMock()
    
    await engine.disconnect_provider(conn_id)
    
    # Verify credentials cleared
    assert mock_conn.credentials_json == {}
    
    # Verify DB update called
    engine.integration_repo.update_connection_status.assert_called_once_with(conn_id, ConnectionStatus.DISCONNECTED.value)
    
    # Verify event published
    mock_event_bus.publish.assert_called_once()
    event_called = mock_event_bus.publish.call_args[0][0]
    assert event_called.event_name == "integration.disconnected"
