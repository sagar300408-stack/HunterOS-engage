from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.health.models import HealthSnapshot


class HealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_snapshot(self, snapshot: HealthSnapshot) -> HealthSnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_snapshots(self, target_type: str, target_id: UUID) -> List[HealthSnapshot]:
        """
        Returns the latest health snapshot for every health domain for a given target.
        """
        stmt = select(HealthSnapshot).where(
            HealthSnapshot.target_type == target_type,
            HealthSnapshot.target_id == target_id
        ).order_by(
            HealthSnapshot.health_name, HealthSnapshot.calculated_at.desc()
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        # Deduplicate to keep only the latest per health_name
        latest = {}
        for row in rows:
            if row.health_name not in latest:
                latest[row.health_name] = row
                
        return list(latest.values())

    async def get_health_trends(self, target_type: str, target_id: UUID, health_name: str, limit: int = 30) -> List[HealthSnapshot]:
        """
        Returns the historical snapshots for a specific health domain to build trends.
        """
        stmt = select(HealthSnapshot).where(
            HealthSnapshot.target_type == target_type,
            HealthSnapshot.target_id == target_id,
            HealthSnapshot.health_name == health_name
        ).order_by(
            HealthSnapshot.calculated_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
