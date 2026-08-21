from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domain.integration.models import IntegrationConnection


class IntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_connection(self, connection_id: UUID) -> Optional[IntegrationConnection]:
        stmt = select(IntegrationConnection).where(IntegrationConnection.id == connection_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_connections_by_workspace(self, workspace_id: UUID) -> List[IntegrationConnection]:
        stmt = select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == workspace_id,
            IntegrationConnection.status.in_(["connected", "degraded"])
        ).order_by(IntegrationConnection.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_connection_by_connector(self, workspace_id: UUID, connector_id: str) -> Optional[IntegrationConnection]:
        stmt = select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == workspace_id,
            IntegrationConnection.connector_id == connector_id,
            IntegrationConnection.status.in_(["connected", "degraded"])
        ).order_by(IntegrationConnection.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save_connection(self, connection: IntegrationConnection) -> IntegrationConnection:
        self.session.add(connection)
        await self.session.commit()
        await self.session.refresh(connection)
        return connection
        
    async def update_connection_status(self, connection_id: UUID, status: str, error_message: Optional[str] = None) -> None:
        stmt = update(IntegrationConnection).where(
            IntegrationConnection.id == connection_id
        ).values(status=status, error_message=error_message)
        await self.session.execute(stmt)
        await self.session.commit()
