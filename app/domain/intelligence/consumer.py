import logging
from app.events.bus.interfaces import EventConsumer
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.integrations.postgres.database import get_session
from app.domain.intelligence.engines.pipeline import OperationalIntelligencePipeline

logger = logging.getLogger(__name__)

class IntelligenceEventConsumer(EventConsumer):
    """
    Subscribes to all state-changing events.
    Priority is -10 to run after projections.
    Orchestrates the entire Operational Intelligence Pipeline.
    """
    
    def get_priority(self) -> int:
        return -10

    def get_subscriptions(self) -> list[type]:
        return [UniversalBaseEvent]
        
    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not event.workspace_id:
            return

        # Do not recursively trigger intelligence on our own events
        if event.metadata.category.value in ["FRICTION", "INTELLIGENCE"]:
            return

        logger.debug(f"IntelligenceEventConsumer handling event: {event.metadata.event_type}")

        async with get_session() as session:
            try:
                pipeline = OperationalIntelligencePipeline(session)
                await pipeline.run(event.workspace_id)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in Operational Intelligence Pipeline for event {event.metadata.event_type}: {str(e)}", exc_info=True)

    async def register(self, bus: EventBus) -> None:
        await bus.subscribe(self)
