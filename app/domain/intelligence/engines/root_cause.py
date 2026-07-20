import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.models import RootCauseAnalysis
from app.domain.friction.models import FrictionEvent, FrictionType
from app.domain.followup.models import FollowUpQueue


class RootCauseEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.CAPACITY_THRESHOLD = 35 # Configurable expected capacity

    async def analyze(self, workspace_id: uuid.UUID) -> List[RootCauseAnalysis]:
        """
        Scans current friction events and attempts to correlate them with systemic issues.
        """
        now = datetime.now(timezone.utc)
        root_causes = []

        # Find open lead response delays and missed follow-ups
        friction_result = await self.session.execute(
            select(FrictionEvent)
            .where(
                FrictionEvent.workspace_id == workspace_id,
                FrictionEvent.resolved_at == None
            )
        )
        events = friction_result.scalars().all()

        for event in events:
            # Avoid re-analyzing if we already have a root cause for this event
            existing = await self.session.execute(
                select(RootCauseAnalysis)
                .where(RootCauseAnalysis.target_event_id == event.id)
            )
            if existing.scalars().first():
                continue

            if event.friction_type in (FrictionType.LEAD_RESPONSE_DELAY.value, FrictionType.MISSED_FOLLOWUP.value):
                # Check workload
                workload_result = await self.session.execute(
                    select(func.count(FollowUpQueue.id))
                    .where(
                        FollowUpQueue.workspace_id == workspace_id,
                        FollowUpQueue.status == "scheduled"
                    )
                )
                pending_count = workload_result.scalar() or 0

                if pending_count > self.CAPACITY_THRESHOLD:
                    probability = min(0.95, 0.50 + ((pending_count - self.CAPACITY_THRESHOLD) * 0.01))
                    
                    rca = RootCauseAnalysis(
                        workspace_id=workspace_id,
                        target_event_type="friction",
                        target_event_id=event.id,
                        cause_category="CAPACITY_EXCEEDED",
                        explanation=f"Team overloaded: workload is {pending_count} leads vs expected capacity of {self.CAPACITY_THRESHOLD}.",
                        confidence_score=round(probability, 2),
                        metadata_json={"pending_count": pending_count, "capacity": self.CAPACITY_THRESHOLD}
                    )
                    self.session.add(rca)
                    root_causes.append(rca)

        return root_causes
