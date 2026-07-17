import uuid
import pytest
from unittest.mock import AsyncMock

from app.domain.marketplace.engine import MarketplaceEngine
from app.domain.marketplace.models import ConnectorDefinition, InstalledConnector, InstallationStatus
from app.domain.marketplace.schemas import InstallConnectorRequest, UpgradeConnectorRequest
from app.domain.marketplace.compatibility import CompatibilityService

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
from app.domain.approval import models as approval_models
from app.domain.marketplace import models as marketplace_models


@pytest.mark.asyncio
async def test_compatibility_service_semver():
    # Platform is 1.0.0
    CompatibilityService.PLATFORM_VERSION = "1.0.0"
    
    assert CompatibilityService.is_compatible_with_platform(">=1.0.0") == True
    assert CompatibilityService.is_compatible_with_platform(">=1.1.0") == False
    assert CompatibilityService.is_compatible_with_platform(">=0.9.0,<2.0.0") == True

    # Upgrades
    assert CompatibilityService.is_upgrade_allowed("1.0.0", "1.1.0") == True
    assert CompatibilityService.is_upgrade_allowed("1.1.0", "1.0.0") == False
    assert CompatibilityService.is_upgrade_allowed("1.0.0", "1.0.0") == False


@pytest.mark.asyncio
async def test_marketplace_install_connector():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    engine = MarketplaceEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    
    def_mock = ConnectorDefinition(
        connector_id="test_crm",
        version="1.0.0",
        supported_platform_versions=">=1.0.0"
    )
    
    engine.repo.get_connector_definition = AsyncMock(return_value=def_mock)
    
    async def mock_save_install(ins):
        ins.id = uuid.uuid4()
        return ins
        
    engine.repo.save_installed_connector = AsyncMock(side_effect=mock_save_install)
    
    req = InstallConnectorRequest(
        connector_id="test_crm",
        version="1.0.0",
        requested_by="admin"
    )
    
    installation = await engine.install_connector(workspace_id, req)
    
    assert installation.connector_id == "test_crm"
    assert installation.installation_version == "1.0.0"
    assert installation.status == InstallationStatus.PENDING_CONFIG.value
    assert mock_event_bus.publish.call_count == 1
    
    # Test version mismatch rejection
    req_bad_version = InstallConnectorRequest(
        connector_id="test_crm",
        version="1.1.0",
        requested_by="admin"
    )
    
    with pytest.raises(ValueError):
        await engine.install_connector(workspace_id, req_bad_version)
        
    # Test platform incompatibility rejection
    def_mock.supported_platform_versions = ">=2.0.0"
    with pytest.raises(ValueError):
        await engine.install_connector(workspace_id, req)


@pytest.mark.asyncio
async def test_marketplace_upgrade_connector():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    engine = MarketplaceEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    installation_id = uuid.uuid4()
    
    ins_mock = InstalledConnector(
        id=installation_id,
        workspace_id=workspace_id,
        connector_id="test_crm",
        installation_version="1.0.0"
    )
    
    def_mock = ConnectorDefinition(
        connector_id="test_crm",
        version="1.1.0",
        supported_platform_versions=">=1.0.0"
    )
    
    engine.repo.get_installed_connector = AsyncMock(return_value=ins_mock)
    engine.repo.get_connector_definition = AsyncMock(return_value=def_mock)
    engine.repo.update_installed_connector = AsyncMock(return_value=ins_mock)
    
    req = UpgradeConnectorRequest(target_version="1.1.0")
    
    upgraded = await engine.upgrade_connector(workspace_id, installation_id, req)
    
    assert upgraded.installation_version == "1.1.0"
    
    # Re-upgrade should fail because target_version == current_version (not >)
    with pytest.raises(ValueError):
        await engine.upgrade_connector(workspace_id, installation_id, req)
