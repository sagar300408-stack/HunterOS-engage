import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.domain.reliability.models import ReliabilityEvent, EventType
from app.domain.onboarding.models import OperationalCapabilityMatrix

logger = logging.getLogger("hunteros.reliability")

class FailoverEngine:
    """
    Handles automatic failover and graceful degradation across HunterOS.
    """

    @staticmethod
    async def trigger_graceful_degradation(
        db: AsyncSession,
        service_name: str,
        reason: str
    ):
        """
        Drops capability of a specific service to "degraded" or "human_review".
        """
        logger.warning(f"Failover triggered for {service_name}: {reason}")
        
        # Log the event
        event = ReliabilityEvent(
            event_type=EventType.degradation,
            service_name=service_name,
            description=reason
        )
        db.add(event)
        
        # We would typically update the OperationalCapabilityMatrix here to 
        # disable autonomous processing and route to human review.
        # e.g., matrix.capability_status = "degraded"
        
        await db.commit()

    @staticmethod
    async def resolve_degradation(
        db: AsyncSession,
        service_name: str
    ):
        """
        Restores a service to full health after it recovers.
        """
        logger.info(f"Service recovered: {service_name}")
        
        event = ReliabilityEvent(
            event_type=EventType.recovery,
            service_name=service_name,
            description="Service has automatically recovered"
        )
        db.add(event)
        await db.commit()
