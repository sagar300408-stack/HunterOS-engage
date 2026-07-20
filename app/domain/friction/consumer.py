"""
FrictionEventConsumer
──────────────────────
Subscribes to ALL business events via the EventBus.
On every event, triggers a friction scan for the event's workspace.

Uses the platform session factory to open its own DB session,
keeping it isolated from the request-scoped session.
"""
import logging
from typing import List, Type
from uuid import UUID

from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent

logger = logging.getLogger(__name__)


class FrictionEventConsumer(EventConsumer):
    """Listens to all platform events and triggers friction re-evaluation."""

    def get_priority(self) -> int:
        # Runs last — after event store and projections
        return -10

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        # Subscribe to the base class to receive ALL events
        return [UniversalBaseEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        workspace_id: UUID = event.workspace_id

        logger.debug(
            "friction_consumer_received",
            extra={"event_name": event.event_name, "workspace_id": str(workspace_id)},
        )

        try:
            from app.integrations.postgres.database import get_session_factory
            from app.domain.friction.analyzer import BusinessFrictionAnalyzer

            factory = get_session_factory()
            async with factory() as session:
                async with session.begin():
                    analyzer = BusinessFrictionAnalyzer(session)
                    await analyzer.run_full_scan(workspace_id)
        except Exception as exc:
            logger.error(
                "friction_consumer_error",
                extra={
                    "event_name": event.event_name,
                    "workspace_id": str(workspace_id),
                    "error": str(exc),
                },
                exc_info=True,
            )
