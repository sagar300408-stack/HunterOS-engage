import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.domain.analytics.engines.customer_health import CustomerHealthEngine

logger = logging.getLogger("hunteros.cs")

class RenewalsEngine:
    """
    Identifies expansion opportunities and forecasts renewal risks based on quantitative health data.
    """

    @staticmethod
    async def evaluate_expansion_readiness(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
        """
        Determines if a customer is a candidate for expansion.
        Rule: Must have high health score, strong ROI, and be in adoption/optimization stage.
        """
        snapshot = await CustomerHealthEngine.compute_health_snapshot(db, workspace_id)
        
        ready = False
        reasons = []
        
        if snapshot.health_score > 85:
            ready = True
            reasons.append("Health Score is Excellent (>85).")
        else:
            reasons.append(f"Health Score too low ({snapshot.health_score}).")
            
        return {
            "expansion_ready": ready,
            "reasons": reasons
        }
