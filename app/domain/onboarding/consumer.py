from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from typing import List
from app.domain.onboarding.repository import OnboardingRepository
from app.integrations.postgres.database import get_session

class OnboardingEventConsumer(EventConsumer):
    """
    Listens for business events globally to detect configuration drift and integration health.
    """
    
    @property
    def name(self) -> str:
        return "onboarding_health_consumer"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return 100 # Run late in the process to assess overall health changes

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass
