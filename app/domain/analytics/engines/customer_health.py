import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.domain.analytics.models import CustomerHealthSnapshot, FeatureAdoption
from app.domain.analytics.engines.product_usage import ProductUsageEngine

logger = logging.getLogger("hunteros.analytics")

class CustomerHealthEngine:
    """
    Computes and records an Organization's composite Health Score.
    """

    @staticmethod
    async def compute_health_snapshot(db: AsyncSession, workspace_id: uuid.UUID) -> CustomerHealthSnapshot:
        """
        Calculates a composite health score based on active users and feature adoption.
        """
        # 1. Active Users Component
        wau = await ProductUsageEngine.get_active_users(db, workspace_id, days=7)
        engagement_score = min(wau * 10, 100.0) # Mock scoring logic
        
        # 2. Feature Adoption Component
        stmt = select(func.count(FeatureAdoption.id)).where(
            FeatureAdoption.workspace_id == workspace_id,
            FeatureAdoption.is_adopted == True
        )
        result = await db.execute(stmt)
        adopted_features = result.scalar_one() or 0
        adoption_score = min(adopted_features * 15, 100.0) # Mock scoring logic
        
        # 3. Composite Health Score
        health_score = (engagement_score * 0.6) + (adoption_score * 0.4)
        
        # 4. Risk Assessment
        renewal_risk = "low"
        if health_score < 40:
            renewal_risk = "high"
        elif health_score < 70:
            renewal_risk = "medium"
            
        snapshot = CustomerHealthSnapshot(
            workspace_id=workspace_id,
            health_score=health_score,
            adoption_score=adoption_score,
            engagement_score=engagement_score,
            renewal_risk=renewal_risk
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        
        return snapshot
