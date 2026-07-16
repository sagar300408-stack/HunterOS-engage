from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.briefing.models import BriefingSnapshot


class BriefingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_briefing(self, briefing: BriefingSnapshot) -> BriefingSnapshot:
        self.session.add(briefing)
        await self.session.commit()
        await self.session.refresh(briefing)
        return briefing

    async def get_latest_briefing(self, workspace_id: UUID, template_name: str) -> Optional[BriefingSnapshot]:
        stmt = select(BriefingSnapshot).where(
            BriefingSnapshot.workspace_id == workspace_id,
            BriefingSnapshot.template_name == template_name
        ).order_by(BriefingSnapshot.generated_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_briefing_history(self, workspace_id: UUID, template_name: str, limit: int = 10) -> List[BriefingSnapshot]:
        stmt = select(BriefingSnapshot).where(
            BriefingSnapshot.workspace_id == workspace_id,
            BriefingSnapshot.template_name == template_name
        ).order_by(BriefingSnapshot.generated_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_briefings_by_period(self, workspace_id: UUID, period: str, limit: int = 10) -> List[BriefingSnapshot]:
        stmt = select(BriefingSnapshot).where(
            BriefingSnapshot.workspace_id == workspace_id,
            BriefingSnapshot.period == period
        ).order_by(BriefingSnapshot.generated_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
