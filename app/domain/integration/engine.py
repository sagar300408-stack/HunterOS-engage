import logging
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.integration.repository import IntegrationRepository
from app.domain.integration.models import IntegrationConnection, ConnectionStatus
from app.domain.integration.credentials import CredentialProvider
from app.domain.integration.connectors.registry import connector_registry
from app.domain.integration.schemas import ConnectorMetadata
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


logger = logging.getLogger(__name__)


class IntegrationEngine:
    """
    Engine responsible for orchestrating the connection lifecycle.
    """
    def __init__(self, session: AsyncSession, cred_provider: CredentialProvider, event_bus: EventBus) -> None:
        self.session = session
        self.integration_repo = IntegrationRepository(session)
        self.cred_provider = cred_provider
        self.event_bus = event_bus
        
    def get_available_connectors(self) -> List[ConnectorMetadata]:
        return [c.metadata for c in connector_registry.get_all_connectors()]

    async def connect_provider(
        self, 
        workspace_id: UUID, 
        connector_id: str, 
        name: str, 
        credentials: Dict[str, Any], 
        settings: Dict[str, Any]
    ) -> IntegrationConnection:
        
        connector = connector_registry.get_connector(connector_id)
        if not connector:
            raise ValueError(f"Connector '{connector_id}' not found.")
            
        # Initialize Connection Model
        connection = IntegrationConnection(
            workspace_id=workspace_id,
            connector_id=connector_id,
            connector_type=connector.metadata.connector_type,
            provider=connector.metadata.provider,
            name=name,
            settings=settings
        )
        
        # Store Credentials securely via Provider
        self.cred_provider.store_credentials(connection, credentials)
        
        # Test Health
        status, error_msg = await connector.health_check(credentials, settings)
        
        connection.status = status
        connection.error_message = error_msg
        
        # Save to DB
        saved_conn = await self.integration_repo.save_connection(connection)
        
        # Publish Event
        await self._publish_lifecycle_event(
            workspace_id=workspace_id,
            connection_id=saved_conn.id,
            status=status,
            event_name="integration.connected" if status in [ConnectionStatus.CONNECTED.value, ConnectionStatus.DEGRADED.value] else "integration.connection_failed"
        )
        
        return saved_conn
        
    async def disconnect_provider(self, connection_id: UUID) -> None:
        conn = await self.integration_repo.get_connection(connection_id)
        if not conn:
            raise ValueError("Connection not found.")
            
        # Wipe Credentials
        self.cred_provider.clear_credentials(conn)
        
        # Update Status
        await self.integration_repo.update_connection_status(connection_id, ConnectionStatus.DISCONNECTED.value)
        
        # Publish Event
        await self._publish_lifecycle_event(
            workspace_id=conn.workspace_id,
            connection_id=connection_id,
            status=ConnectionStatus.DISCONNECTED.value,
            event_name="integration.disconnected"
        )
        
    async def _publish_lifecycle_event(self, workspace_id: UUID, connection_id: UUID, status: str, event_name: str) -> None:
        event = UniversalBaseEvent(
            workspace_id=workspace_id,
            category=EventCategory.PLATFORM,
            event_name=event_name,
            metadata={
                "connection_id": str(connection_id),
                "status": status
            },
            actor_type=ActorType.SYSTEM,
            source_subsystem="integration_engine"
        )
        await self.event_bus.publish(event)
