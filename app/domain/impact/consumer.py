from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from typing import List
from app.domain.impact.engines.collector import ImpactCollector
from app.domain.impact.repository import ImpactRepository
from app.domain.impact.models import ImpactEvent
from app.integrations.postgres.database import get_session

class ImpactEventConsumer(EventConsumer):
    """
    Listens for business events globally and calculates ROI and Value Attribution.
    """
    
    @property
    def name(self) -> str:
        return "impact_roi_collector"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return 20 # Runs after core processing

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        # Ignore our own reports being generated
        if getattr(event, 'event_name', '').startswith("impact."):
            return
            
        async with get_session() as session:
            repo = ImpactRepository(session)
            
            # Map HunterEvent to ImpactEvent
            impact_event = ImpactEvent(
                workspace_id=event.workspace_id,
                event_type=event.type,
                source_feature=event.payload.get("source_feature", "unknown"),
                payload=event.payload
            )
            
            await ImpactCollector.process_event(repo, impact_event)
