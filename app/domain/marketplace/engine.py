from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
import jsonschema

from app.domain.marketplace.models import ConnectorDefinition, InstalledConnector, ConnectorHealthRecord, InstallationStatus, HealthLatencyBucket
from app.domain.marketplace.schemas import InstallConnectorRequest, ConfigureConnectorRequest, UpgradeConnectorRequest
from app.domain.marketplace.repository import MarketplaceRepository
from app.domain.marketplace.compatibility import CompatibilityService
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


class MarketplaceEngine:
    def __init__(self, session: AsyncSession, event_bus: EventBus):
        self.session = session
        self.repo = MarketplaceRepository(session)
        self.event_bus = event_bus

    async def list_available_connectors(self) -> List[ConnectorDefinition]:
        return await self.repo.get_active_connector_definitions()

    async def install_connector(self, workspace_id: UUID, req: InstallConnectorRequest) -> InstalledConnector:
        definition = await self.repo.get_connector_definition(req.connector_id)
        if not definition:
            raise ValueError(f"Connector {req.connector_id} not found.")

        if definition.version != req.version:
            raise ValueError(f"Requested version {req.version} does not match available version {definition.version}.")

        if not CompatibilityService.validate_installation(definition):
            raise ValueError(f"Connector {definition.connector_id} v{definition.version} is not compatible with the current platform version.")

        installation = InstalledConnector(
            workspace_id=workspace_id,
            connector_id=definition.connector_id,
            installation_version=definition.version,
            status=InstallationStatus.PENDING_CONFIG.value,
            enabled=False
        )

        installation = await self.repo.save_installed_connector(installation)
        
        await self._publish_event(workspace_id, "connector.installed", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id,
            "version": installation.installation_version
        })
        
        return installation

    async def configure_connector(self, workspace_id: UUID, installation_id: UUID, req: ConfigureConnectorRequest) -> InstalledConnector:
        installation = await self.repo.get_installed_connector(installation_id)
        if not installation or installation.workspace_id != workspace_id:
            raise ValueError("Installation not found.")

        definition = await self.repo.get_connector_definition(installation.connector_id)
        
        # Validate configuration schema
        try:
            jsonschema.validate(instance=req.configuration, schema=definition.configuration_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e.message}")

        installation.configuration = req.configuration
        
        if req.credential_reference:
            installation.credential_reference = req.credential_reference

        # If it was pending config, move to active (but not yet enabled)
        if installation.status == InstallationStatus.PENDING_CONFIG.value:
            installation.status = InstallationStatus.ACTIVE.value

        installation = await self.repo.update_installed_connector(installation)

        await self._publish_event(workspace_id, "connector.configured", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id
        })

        return installation

    async def enable_connector(self, workspace_id: UUID, installation_id: UUID) -> InstalledConnector:
        installation = await self.repo.get_installed_connector(installation_id)
        if not installation or installation.workspace_id != workspace_id:
            raise ValueError("Installation not found.")

        if installation.status == InstallationStatus.PENDING_CONFIG.value:
            raise ValueError("Cannot enable connector: Configuration is pending.")

        installation.enabled = True
        installation = await self.repo.update_installed_connector(installation)

        await self._publish_event(workspace_id, "connector.enabled", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id
        })

        return installation

    async def disable_connector(self, workspace_id: UUID, installation_id: UUID) -> InstalledConnector:
        installation = await self.repo.get_installed_connector(installation_id)
        if not installation or installation.workspace_id != workspace_id:
            raise ValueError("Installation not found.")

        installation.enabled = False
        installation = await self.repo.update_installed_connector(installation)

        await self._publish_event(workspace_id, "connector.disabled", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id
        })

        return installation

    async def upgrade_connector(self, workspace_id: UUID, installation_id: UUID, req: UpgradeConnectorRequest) -> InstalledConnector:
        installation = await self.repo.get_installed_connector(installation_id)
        if not installation or installation.workspace_id != workspace_id:
            raise ValueError("Installation not found.")
            
        definition = await self.repo.get_connector_definition(installation.connector_id)

        if not CompatibilityService.is_upgrade_allowed(installation.installation_version, req.target_version):
            raise ValueError("Invalid upgrade path.")
            
        if definition.version != req.target_version:
             raise ValueError(f"Target version {req.target_version} is not the current available version.")

        if not CompatibilityService.validate_installation(definition):
            raise ValueError("Target version is not compatible with the current platform version.")

        installation.installation_version = req.target_version
        installation = await self.repo.update_installed_connector(installation)

        await self._publish_event(workspace_id, "connector.upgraded", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id,
            "version": installation.installation_version
        })

        return installation

    async def record_health_check(self, workspace_id: UUID, installation_id: UUID, status: str, response_time_ms: int, message: Optional[str] = None) -> ConnectorHealthRecord:
        installation = await self.repo.get_installed_connector(installation_id)
        if not installation:
            raise ValueError("Installation not found.")

        # Determine latency bucket
        latency_bucket = HealthLatencyBucket.LOW.value
        if response_time_ms > 1000:
            latency_bucket = HealthLatencyBucket.HIGH.value
        elif response_time_ms > 300:
            latency_bucket = HealthLatencyBucket.MEDIUM.value

        record = ConnectorHealthRecord(
            installation_id=installation_id,
            status=status,
            response_time_ms=response_time_ms,
            latency_bucket=latency_bucket,
            message=message
        )
        
        if status == "ERROR":
            record.failure_count = 1
        
        record = await self.repo.save_health_record(record)
        
        await self._publish_event(workspace_id, "connector.health_changed", {
            "installation_id": str(installation.id),
            "connector_id": installation.connector_id,
            "status": status,
            "latency": latency_bucket
        })

        return record

    async def _publish_event(self, workspace_id: UUID, event_name: str, metadata: Dict[str, Any]) -> None:
        event = UniversalBaseEvent(
            workspace_id=workspace_id,
            category=EventCategory.MARKETPLACE,
            event_name=event_name,
            correlation_id=None,
            metadata=metadata,
            actor_type=ActorType.SYSTEM,
            source_subsystem="marketplace_engine"
        )
        await self.event_bus.publish(event)
