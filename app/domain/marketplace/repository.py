from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.marketplace.models import ConnectorDefinition, InstalledConnector, ConnectorHealthRecord, ConnectorStatus


class MarketplaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Connector Definitions ---
    
    async def get_active_connector_definitions(self) -> List[ConnectorDefinition]:
        stmt = select(ConnectorDefinition).where(ConnectorDefinition.status == ConnectorStatus.ACTIVE.value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_connector_definition(self, connector_id: str) -> Optional[ConnectorDefinition]:
        stmt = select(ConnectorDefinition).where(ConnectorDefinition.connector_id == connector_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def save_connector_definition(self, definition: ConnectorDefinition) -> ConnectorDefinition:
        self.session.add(definition)
        await self.session.commit()
        await self.session.refresh(definition)
        return definition

    # --- Installed Connectors ---
    
    async def get_installed_connectors(self, workspace_id: UUID) -> List[InstalledConnector]:
        stmt = select(InstalledConnector).where(InstalledConnector.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
        
    async def get_installed_connector(self, installation_id: UUID) -> Optional[InstalledConnector]:
        stmt = select(InstalledConnector).where(InstalledConnector.id == installation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_installed_connector(self, installation: InstalledConnector) -> InstalledConnector:
        self.session.add(installation)
        await self.session.commit()
        await self.session.refresh(installation)
        return installation

    async def update_installed_connector(self, installation: InstalledConnector) -> InstalledConnector:
        self.session.add(installation)
        await self.session.commit()
        await self.session.refresh(installation)
        return installation

    async def delete_installed_connector(self, installation: InstalledConnector) -> None:
        await self.session.delete(installation)
        await self.session.commit()

    # --- Health Records ---
    
    async def get_health_records(self, installation_id: UUID, limit: int = 50) -> List[ConnectorHealthRecord]:
        stmt = select(ConnectorHealthRecord).where(
            ConnectorHealthRecord.installation_id == installation_id
        ).order_by(ConnectorHealthRecord.checked_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_health_record(self, record: ConnectorHealthRecord) -> ConnectorHealthRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
