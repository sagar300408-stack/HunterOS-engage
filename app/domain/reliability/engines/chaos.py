import logging
import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.domain.reliability.models import ReliabilityEvent, EventType

logger = logging.getLogger("hunteros.chaos")

class ChaosEngine:
    """
    Simulates controlled failures to validate resilience and MTTR.
    Should ONLY be activated in lower environments or via strict Feature Flags.
    """

    @staticmethod
    async def inject_latency(db: AsyncSession, service_name: str, min_ms: int = 100, max_ms: int = 2000):
        """
        Artificially sleeps to simulate network latency to a downstream service.
        """
        latency = random.randint(min_ms, max_ms)
        logger.warning(f"Chaos: Injecting {latency}ms latency into {service_name}")
        
        await asyncio.sleep(latency / 1000.0)
        
    @staticmethod
    async def trigger_service_failure(db: AsyncSession, service_name: str):
        """
        Simulates a hard failure of a dependency to ensure failover logic executes.
        """
        logger.error(f"Chaos: Triggering simulated failure for {service_name}")
        
        event = ReliabilityEvent(
            event_type=EventType.chaos_experiment,
            service_name=service_name,
            description=f"Simulated failure via Chaos Engine"
        )
        db.add(event)
        await db.commit()
        
        # In actual practice, this might flip a Redis key that interceptors read 
        # to block traffic or raise simulated Exceptions.
        raise ConnectionError(f"Simulated Chaos Failure: {service_name} is unavailable")
