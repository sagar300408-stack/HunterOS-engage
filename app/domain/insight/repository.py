from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domain.insight.models import InsightSnapshot, InsightLifecycle


class InsightRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_insight_by_generator(self, target_type: str, target_id: UUID, generator_name: str) -> Optional[InsightSnapshot]:
        stmt = select(InsightSnapshot).where(
            InsightSnapshot.target_type == target_type,
            InsightSnapshot.target_id == target_id,
            InsightSnapshot.generator_name == generator_name,
            InsightSnapshot.lifecycle_status == InsightLifecycle.ACTIVE.value
        ).order_by(InsightSnapshot.generated_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def supersede_insight(self, insight_id: UUID) -> None:
        """
        Marks an insight as SUPERSEDED.
        """
        stmt = update(InsightSnapshot).where(
            InsightSnapshot.id == insight_id
        ).values(lifecycle_status=InsightLifecycle.SUPERSEDED.value)
        await self.session.execute(stmt)
        await self.session.commit()

    async def save_insight(self, insight: InsightSnapshot) -> InsightSnapshot:
        """
        Saves a new insight. If there is already an active insight from the same generator,
        it supersedes the old one to prevent duplicates.
        """
        active_insight = await self.get_active_insight_by_generator(
            insight.target_type, insight.target_id, insight.generator_name
        )
        
        if active_insight:
            # Check if it's identical or needs superseding. 
            # In this engine, we simply supersede old active insights for the same generator/target 
            # so the latest insight rules.
            await self.supersede_insight(active_insight.id)
            
        self.session.add(insight)
        await self.session.commit()
        await self.session.refresh(insight)
        return insight

    async def get_latest_insights(self, target_type: str, target_id: UUID, limit: int = 20) -> List[InsightSnapshot]:
        """
        Fetches the latest active insights.
        """
        stmt = select(InsightSnapshot).where(
            InsightSnapshot.target_type == target_type,
            InsightSnapshot.target_id == target_id,
            InsightSnapshot.lifecycle_status == InsightLifecycle.ACTIVE.value
        ).order_by(
            InsightSnapshot.generated_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
