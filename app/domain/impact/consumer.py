from app.events.bus.event_bus import EventConsumer, HunterEvent
from app.domain.impact.engines.collector import ImpactCollector
from app.domain.impact.repository import ImpactRepository
from app.domain.impact.models import ImpactEvent
from app.integrations.postgres.database import SessionLocal

class ImpactEventConsumer(EventConsumer):
    """
    Listens for business events globally and calculates ROI and Value Attribution.
    """
    
    @property
    def name(self) -> str:
        return "impact_roi_collector"

    @property
    def priority(self) -> int:
        return 20 # Runs after core processing

    async def process(self, event: HunterEvent) -> None:
        # Ignore our own reports being generated
        if event.type.startswith("impact."):
            return
            
        async with SessionLocal() as session:
            repo = ImpactRepository(session)
            
            # Map HunterEvent to ImpactEvent
            impact_event = ImpactEvent(
                workspace_id=event.workspace_id,
                event_type=event.type,
                source_feature=event.payload.get("source_feature", "unknown"),
                payload=event.payload
            )
            
            await ImpactCollector.process_event(repo, impact_event)
