from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domain.recommendation.models import RecommendationSnapshot, RecommendationLifecycle


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_recommendation_by_generator(self, target_type: str, target_id: UUID, generator_name: str) -> Optional[RecommendationSnapshot]:
        stmt = select(RecommendationSnapshot).where(
            RecommendationSnapshot.target_type == target_type,
            RecommendationSnapshot.target_id == target_id,
            RecommendationSnapshot.generator_name == generator_name,
            RecommendationSnapshot.lifecycle_status == RecommendationLifecycle.ACTIVE.value
        ).order_by(RecommendationSnapshot.generated_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, recommendation_id: UUID, new_status: str) -> None:
        """
        Updates the lifecycle status of a recommendation.
        """
        stmt = update(RecommendationSnapshot).where(
            RecommendationSnapshot.id == recommendation_id
        ).values(lifecycle_status=new_status)
        await self.session.execute(stmt)
        await self.session.commit()

    async def supersede_recommendation(self, recommendation_id: UUID) -> None:
        """
        Marks a recommendation as SUPERSEDED.
        """
        await self.update_status(recommendation_id, RecommendationLifecycle.SUPERSEDED.value)

    async def save_recommendation(self, recommendation: RecommendationSnapshot) -> RecommendationSnapshot:
        """
        Saves a new recommendation. If there is already an active recommendation from the same generator,
        it supersedes the old one to prevent duplicates.
        """
        active_rec = await self.get_active_recommendation_by_generator(
            recommendation.target_type, recommendation.target_id, recommendation.generator_name
        )
        
        if active_rec:
            # Supersede old active recommendation so the newest one is presented
            await self.supersede_recommendation(active_rec.id)
            
        self.session.add(recommendation)
        await self.session.commit()
        await self.session.refresh(recommendation)
        return recommendation

    async def get_latest_recommendations(self, target_type: str, target_id: UUID, limit: int = 20) -> List[RecommendationSnapshot]:
        """
        Fetches the latest active recommendations.
        """
        stmt = select(RecommendationSnapshot).where(
            RecommendationSnapshot.target_type == target_type,
            RecommendationSnapshot.target_id == target_id,
            RecommendationSnapshot.lifecycle_status == RecommendationLifecycle.ACTIVE.value
        ).order_by(
            RecommendationSnapshot.recommendation_score.desc(),
            RecommendationSnapshot.generated_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
