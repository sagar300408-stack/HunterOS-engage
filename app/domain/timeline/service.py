from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.timeline.models import TimelineEntry
from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.strategies.registry import timeline_strategy_registry
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.projections.base import BaseEventProjection


class TimelineProjection(BaseEventProjection):
    """
    Projection responsible for converting UniversalBaseEvents into TimelineEntries.
    """
    @property
    def name(self) -> str:
        return "TimelineProjection"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Generates human-readable activity timeline entries from business events."

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

    def __init__(self, repository: TimelineRepository):
        self.repository = repository

    async def project_event(self, event: UniversalBaseEvent, session: AsyncSession, **kwargs: Any) -> Optional[TimelineEntry]:
        """
        Projects an event to a TimelineEntry without mutating the original event.
        Uses the Strategy Registry to extract structured data and severity.
        """
        strategy = timeline_strategy_registry.get_strategy(event.category, event.event_name)
        
        structured_data = strategy.extract_structured_data(event)
        
        entry = TimelineEntry(
            event_id=event.event_id,
            workspace_id=event.workspace_id,
            customer_id=event.customer_id,
            conversation_id=event.conversation_id,
            lead_id=event.lead_id,
            occurred_at=event.occurred_at,
            activity_type=strategy.activity_type,
            severity=strategy.default_severity,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            source_subsystem=event.source_subsystem,
            structured_data=structured_data
        )
        
        return await self.repository.add_entry(session, entry)


class TimelineQueryService:
    """
    Query service that retrieves TimelineEntries and formats their UI text dynamically.
    """
    def __init__(self, repository: TimelineRepository):
        self.repository = repository

    def _format_entry(self, entry: TimelineEntry, event_category: Any = None, event_name: str = "") -> TimelineEntryResponse:
        """
        Helper to map the dynamic formatting from the strategy.
        Note: Since TimelineEntry does not store the original category and name, 
        we rely on the strategy registry's default fallback or a future mapping from activity_type.
        For exact match, we can either store category/name in TimelineEntry, or map from activity_type.
        Let's assume activity_type uniquely identifies the strategy logic. 
        Wait, currently the registry is by (category, event_name). We might need to store those or look up by activity_type.
        For simplicity, let's reverse lookup by activity_type or just store them in structured_data.
        """
        # If we didn't store event_name, we can use the fallback. 
        # But wait! structured_data could contain them, or we can just iterate.
        # Actually, let's just use a naive lookup or the fallback if not found.
        # A better approach is to have a registry mapping activity_type -> strategy.
        # For now, we will simulate this by checking all registered strategies.
        strategy = None
        for strat in timeline_strategy_registry._strategies.values():
            if strat.activity_type == entry.activity_type:
                strategy = strat
                break
        
        if not strategy:
            strategy = timeline_strategy_registry._default

        formatted = strategy.format_for_display(entry.structured_data)
        
        return TimelineEntryResponse(
            timeline_id=entry.timeline_id,
            event_id=entry.event_id,
            workspace_id=entry.workspace_id,
            customer_id=entry.customer_id,
            conversation_id=entry.conversation_id,
            occurred_at=entry.occurred_at,
            activity_title=formatted.title,
            activity_description=formatted.description,
            activity_type=entry.activity_type,
            severity=entry.severity,
            actor_type=entry.actor_type,
            actor_id=entry.actor_id,
            source_subsystem=entry.source_subsystem
        )

    async def get_workspace_timeline(
        self, session: AsyncSession, workspace_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[TimelineEntryResponse]:
        entries = await self.repository.get_timeline(
            session, workspace_id=workspace_id, limit=limit, offset=offset
        )
        return [self._format_entry(e) for e in entries]

    async def get_customer_timeline(
        self, session: AsyncSession, workspace_id: UUID, customer_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[TimelineEntryResponse]:
        entries = await self.repository.get_timeline(
            session, workspace_id=workspace_id, customer_id=customer_id, limit=limit, offset=offset
        )
        return [self._format_entry(e) for e in entries]

    async def get_conversation_timeline(
        self, session: AsyncSession, workspace_id: UUID, conversation_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[TimelineEntryResponse]:
        entries = await self.repository.get_timeline(
            session, workspace_id=workspace_id, conversation_id=conversation_id, limit=limit, offset=offset
        )
        return [self._format_entry(e) for e in entries]
