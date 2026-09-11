from typing import List

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.integration_events import IntegrationConnected, IntegrationDisconnected
from app.domain.onboarding.engines.validation import ValidationEngine
from app.domain.onboarding.engines.golive import GoliveEngine
from app.integrations.postgres.database import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)

class OnboardingEventConsumer(EventConsumer):
    """
    Listens for critical events (like integration state changes)
    to automatically trigger a re-validation and go-live assessment
    for the affected workspace.
    """
    
    @property
    def name(self) -> str:
        return "onboarding_health_consumer"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        # Only listen for events that actually affect readiness state
        return [IntegrationConnected, IntegrationDisconnected]

    def get_priority(self) -> int:
        return 10  # Low priority, runs after core logic

    def get_execution_policy(self) -> ExecutionPolicy:
        # Background is appropriate, as we don't need to block the user action
        return ExecutionPolicy.BACKGROUND

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if isinstance(event, (IntegrationConnected, IntegrationDisconnected)):
            logger.info("onboarding_consumer_triggered", event_type=event.event_type, workspace_id=str(event.workspace_id))
            
            async with get_session() as session:
                async with session.begin():
                    # 1. Re-run validation checks
                    val_engine = ValidationEngine(session)
                    await val_engine.run_checks(event.workspace_id)
                    
                    # 2. Re-compute go-live readiness
                    golive_engine = GoliveEngine(session)
                    await golive_engine.execute(event.workspace_id)
                    
            logger.info("onboarding_state_recomputed", workspace_id=str(event.workspace_id))

