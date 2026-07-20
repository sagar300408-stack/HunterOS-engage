from app.events.bus.event_bus import EventConsumer, HunterEvent
from app.domain.context.engines.learning import ContextLearningEngine
from app.domain.context.repository import ContextRepository
from app.integrations.postgres.database import SessionLocal

class ContextEventConsumer(EventConsumer):
    """
    Listens for business events globally to learn and update the knowledge graph.
    """
    
    @property
    def name(self) -> str:
        return "context_learning_consumer"

    @property
    def priority(self) -> int:
        return -20 # Run early to ensure context is updated before decisions

    async def process(self, event: HunterEvent) -> None:
        async with SessionLocal() as session:
            repo = ContextRepository(session)
            
            await ContextLearningEngine.process_event(
                repo=repo,
                workspace_id=event.workspace_id,
                event_type=event.type,
                payload=event.payload
            )
