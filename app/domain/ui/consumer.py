from app.events.bus.event_bus import EventConsumer, HunterEvent
from app.integrations.postgres.database import SessionLocal

class UIEventConsumer(EventConsumer):
    """
    Listens for business events to seed default UI layouts and track UX analytics asynchronously.
    """
    
    @property
    def name(self) -> str:
        return "ui_experience_consumer"

    @property
    def priority(self) -> int:
        return 1000 # Run last, purely for presentation/analytics updates

    async def process(self, event: HunterEvent) -> None:
        pass
