from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from typing import List
from app.domain.context.engines.learning import ContextLearningEngine
from app.domain.context.repository import ContextRepository
from app.integrations.postgres.database import get_session

class ContextEventConsumer(EventConsumer):
    """
    Listens for business events globally to learn and update the knowledge graph.
    """
    
    @property
    def name(self) -> str:
        return "context_learning_consumer"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return -20 # Run early to ensure context is updated before decisions

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        async with get_session() as session:
            repo = ContextRepository(session)
            
            await ContextLearningEngine.process_event(
                repo=repo,
                workspace_id=event.workspace_id,
                event_type=event.type,
                payload=event.payload
            )
