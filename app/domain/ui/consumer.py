from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from typing import List
from app.integrations.postgres.database import get_session

class UIEventConsumer(EventConsumer):
    """
    Listens for business events to seed default UI layouts and track UX analytics asynchronously.
    """
    
    @property
    def name(self) -> str:
        return "ui_experience_consumer"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return 1000 # Run last, purely for presentation/analytics updates

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass
