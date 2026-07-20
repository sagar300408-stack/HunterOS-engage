import uuid
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domain.ui.models import (
    UserPreference,
    DashboardDefinition,
    NavigationNode,
    FeatureFlag,
    NotificationPreference,
    UXAnalyticsEvent
)

class UIRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_def(self, workspace_id: uuid.UUID, role_key: str) -> Optional[DashboardDefinition]:
        result = await self.session.execute(
            select(DashboardDefinition).where(
                DashboardDefinition.workspace_id == workspace_id,
                DashboardDefinition.role_key == role_key
            )
        )
        return result.scalars().first()

    async def get_navigation_nodes(self, workspace_id: uuid.UUID) -> List[NavigationNode]:
        result = await self.session.execute(
            select(NavigationNode)
            .where(NavigationNode.workspace_id == workspace_id)
            .order_by(NavigationNode.order_index)
        )
        return result.scalars().all()

    async def get_feature_flags(self, workspace_id: uuid.UUID) -> List[FeatureFlag]:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.workspace_id == workspace_id)
        )
        return result.scalars().all()
        
    async def save_event(self, event: UXAnalyticsEvent):
        self.session.add(event)
        await self.session.commit()
