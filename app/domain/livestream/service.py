import asyncio
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.livestream.manager import livestream_manager
from app.domain.timeline.strategies.registry import timeline_strategy_registry
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.projections.base import BaseEventProjection


class LiveStreamProjection(BaseEventProjection):
    """
    Projection responsible for converting UniversalBaseEvents into real-time operational updates.
    Observes all relevant events and forwards them to the WebSocketConnectionManager.
    """
    @property
    def name(self) -> str:
        return "LiveStreamProjection"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Streams operational updates directly to connected dashboard clients in real-time."

    @property
    def subscribed_categories(self) -> List[EventCategory]:
        return [
            EventCategory.CONVERSATION,
            EventCategory.SCHEDULING,
            EventCategory.FOLLOWUP,
            EventCategory.LEAD,
            EventCategory.CUSTOMER,
            EventCategory.WORKSPACE
        ]

    async def project_event(self, event: UniversalBaseEvent, session: AsyncSession, **kwargs: Any) -> None:
        """
        Projects an event to the live stream.
        Uses the Timeline Strategy Registry to format a lightweight UI payload,
        then broadcasts it to the appropriate workspace.
        """
        # 1. Format the event using the Timeline strategy registry
        # We reuse the logic so the Live Stream gets the same nice titles and descriptions.
        strategy = timeline_strategy_registry.get_strategy(event.category, event.event_name)
        structured_data = strategy.extract_structured_data(event)
        formatted = strategy.format_for_display(structured_data)
        
        # 2. Build the lightweight payload
        payload = {
            "event_type": "operational_update",
            "data": {
                "event_id": str(event.event_id),
                "category": event.category.value if hasattr(event.category, "value") else str(event.category),
                "name": event.event_name,
                "activity_title": formatted.title,
                "activity_description": formatted.description,
                "severity": strategy.default_severity.value if hasattr(strategy.default_severity, "value") else str(strategy.default_severity),
                "occurred_at": event.occurred_at.isoformat(),
                "customer_id": str(event.customer_id) if getattr(event, "customer_id", None) else None,
                "conversation_id": str(event.conversation_id) if getattr(event, "conversation_id", None) else None,
            }
        }
        
        # 3. Broadcast to the isolated workspace (we do not await here if we want strict fire-and-forget,
        # but since project_event is async and broadcasting is fast memory I/O, awaiting is safe.)
        await livestream_manager.broadcast_to_workspace(event.workspace_id, payload)
