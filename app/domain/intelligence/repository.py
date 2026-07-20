from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.models import (
    OperationalHealthSnapshot,
    OpportunityLeakageEvent,
    RootCauseAnalysis,
    PredictionEvent,
    ExecutiveInsight,
    ObservationDebounce
)


class IntelligenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_health_snapshot(self, workspace_id: UUID) -> Optional[OperationalHealthSnapshot]:
        result = await self.session.execute(
            select(OperationalHealthSnapshot)
            .where(OperationalHealthSnapshot.workspace_id == workspace_id)
            .order_by(OperationalHealthSnapshot.calculated_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_active_leakages(self, workspace_id: UUID) -> List[OpportunityLeakageEvent]:
        result = await self.session.execute(
            select(OpportunityLeakageEvent)
            .where(
                OpportunityLeakageEvent.workspace_id == workspace_id,
                OpportunityLeakageEvent.is_recovered == False
            )
            .order_by(OpportunityLeakageEvent.revenue_at_risk.desc())
        )
        return list(result.scalars().all())

    async def get_recent_predictions(self, workspace_id: UUID, limit: int = 5) -> List[PredictionEvent]:
        result = await self.session.execute(
            select(PredictionEvent)
            .where(
                PredictionEvent.workspace_id == workspace_id,
                PredictionEvent.invalidated_at == None
            )
            .order_by(PredictionEvent.confidence_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_insights(self, workspace_id: UUID, limit: int = 5) -> List[ExecutiveInsight]:
        result = await self.session.execute(
            select(ExecutiveInsight)
            .where(ExecutiveInsight.workspace_id == workspace_id)
            .order_by(ExecutiveInsight.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def check_debounce_and_lock(self, workspace_id: UUID, debounce_seconds: int = 30) -> bool:
        """
        Returns True if we should proceed with the scan, False if we are debounced.
        Uses a row-level lock.
        """
        # Ensure row exists
        result = await self.session.execute(
            select(ObservationDebounce)
            .where(ObservationDebounce.workspace_id == workspace_id)
        )
        row = result.scalars().first()

        now = datetime.now(timezone.utc)

        if not row:
            new_row = ObservationDebounce(workspace_id=workspace_id, last_scan_at=now, scan_count=1)
            self.session.add(new_row)
            await self.session.flush()
            return True

        time_since_last_scan = (now - row.last_scan_at).total_seconds()
        
        if time_since_last_scan < debounce_seconds:
            return False  # Debounced

        # Update last scan time
        await self.session.execute(
            update(ObservationDebounce)
            .where(ObservationDebounce.workspace_id == workspace_id)
            .values(last_scan_at=now, scan_count=ObservationDebounce.scan_count + 1)
        )
        await self.session.flush()
        return True
