from app.events.bus.event_bus import EventConsumer, HunterEvent
from app.domain.onboarding.repository import OnboardingRepository
from app.integrations.postgres.database import SessionLocal

class OnboardingEventConsumer(EventConsumer):
    """
    Listens for business events globally to detect configuration drift and integration health.
    """
    
    @property
    def name(self) -> str:
        return "onboarding_health_consumer"

    @property
    def priority(self) -> int:
        return 100 # Run late in the process to assess overall health changes

    async def process(self, event: HunterEvent) -> None:
        pass
