import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import uuid

from app.domain.analytics.models import ProductUsageEvent

logger = logging.getLogger("hunteros.analytics")

class ProductUsageEngine:
    """
    Calculates active usage (DAU, WAU) and session duration.
    """

    @staticmethod
    async def log_event(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, event_name: str, duration: int = None, metadata: dict = None):
        """
        Records a single product usage event (e.g. 'login', 'dashboard_view').
        """
        event = ProductUsageEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            event_name=event_name,
            session_duration_seconds=duration,
            metadata_json=metadata or {}
        )
        db.add(event)
        await db.commit()
        
    @staticmethod
    async def get_active_users(db: AsyncSession, workspace_id: uuid.UUID, days: int = 7) -> int:
        """
        Calculates distinct users active in the past N days.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(func.count(func.distinct(ProductUsageEvent.user_id)))
            .where(ProductUsageEvent.workspace_id == workspace_id)
            .where(ProductUsageEvent.timestamp >= cutoff)
        )
        result = await db.execute(stmt)
        return result.scalar_one() or 0
