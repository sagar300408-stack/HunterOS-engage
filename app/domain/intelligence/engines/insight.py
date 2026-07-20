import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.models import ExecutiveInsight, OperationalHealthSnapshot
from app.domain.intelligence.repository import IntelligenceRepository


class InsightEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IntelligenceRepository(session)

    async def generate_insight(self, workspace_id: uuid.UUID, health: OperationalHealthSnapshot) -> ExecutiveInsight:
        """
        Synthesizes the data into a human-readable executive narrative.
        """
        now = datetime.now(timezone.utc)
        
        # Get active leakages
        leakages = await self.repo.get_active_leakages(workspace_id)
        total_leakage = sum(l.revenue_at_risk for l in leakages)

        if health.trend == "DETERIORATING" and health.friction_delta and health.friction_delta > 0:
            narrative = (
                f"Operational performance decreased because Business Friction rose by {health.friction_delta} points. "
            )
            if total_leakage > 0:
                narrative += f"Estimated revenue currently at risk: ₹{total_leakage:,.0f}."
            
            insight = ExecutiveInsight(
                workspace_id=workspace_id,
                insight_type="CRITICAL_ALERT",
                narrative=narrative,
                priority="HIGH",
                created_at=now
            )
        elif health.trend == "IMPROVING":
            narrative = f"Operational performance is improving. Business Friction decreased."
            insight = ExecutiveInsight(
                workspace_id=workspace_id,
                insight_type="POSITIVE_TREND",
                narrative=narrative,
                priority="NORMAL",
                created_at=now
            )
        else:
            narrative = f"Operations are stable. Health Index: {health.health_index}."
            insight = ExecutiveInsight(
                workspace_id=workspace_id,
                insight_type="WEEKLY_SUMMARY",
                narrative=narrative,
                priority="LOW",
                created_at=now
            )

        self.session.add(insight)
        return insight
