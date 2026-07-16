from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.kpi.models import KpiSnapshot


class KpiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_snapshot(self, snapshot: KpiSnapshot) -> KpiSnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_snapshots(self, target_type: str, target_id: UUID) -> List[KpiSnapshot]:
        """
        Returns the latest snapshot for every KPI for a given target.
        For Postgres we could use DISTINCT ON, but to remain engine-agnostic
        we might just order by calculated_at DESC and take the first of each.
        """
        # A simple approach for SQLite/Postgres compatibility:
        # Get all snapshots for the target ordered by calculated_at descending
        stmt = select(KpiSnapshot).where(
            KpiSnapshot.target_type == target_type,
            KpiSnapshot.target_id == target_id
        ).order_by(
            KpiSnapshot.kpi_name, KpiSnapshot.calculated_at.desc()
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        # Deduplicate to keep only the latest per kpi_name
        latest = {}
        for row in rows:
            if row.kpi_name not in latest:
                latest[row.kpi_name] = row
                
        return list(latest.values())

    async def get_kpi_trends(self, target_type: str, target_id: UUID, kpi_name: str, limit: int = 30) -> List[KpiSnapshot]:
        """
        Returns the historical snapshots for a specific KPI to build trends.
        """
        stmt = select(KpiSnapshot).where(
            KpiSnapshot.target_type == target_type,
            KpiSnapshot.target_id == target_id,
            KpiSnapshot.kpi_name == kpi_name
        ).order_by(
            KpiSnapshot.calculated_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
