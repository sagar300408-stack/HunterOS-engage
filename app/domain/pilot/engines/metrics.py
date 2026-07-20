from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging
from typing import Dict, Any

from app.domain.pilot.models import PilotMetrics

logger = logging.getLogger("hunteros.pilot")

class PilotMetricsEngine:
    """
    Captures baseline and current operational metrics to measure pilot success.
    """

    @staticmethod
    async def record_snapshot(
        db: AsyncSession, 
        pilot_id: uuid.UUID, 
        baseline_friction: float,
        current_friction: float,
        weekly_users: int,
        acceptance_rate: float,
        additional: Dict[str, Any] = None
    ) -> PilotMetrics:
        """
        Records a snapshot of adoption and operational friction for the pilot.
        """
        metrics = PilotMetrics(
            pilot_id=pilot_id,
            baseline_friction_score=baseline_friction,
            current_friction_score=current_friction,
            weekly_active_users=weekly_users,
            recommendation_acceptance_rate=acceptance_rate,
            additional_metrics=additional or {}
        )
        db.add(metrics)
        await db.commit()
        await db.refresh(metrics)
        
        logger.info(f"Recorded pilot metrics snapshot for {pilot_id}")
        return metrics
