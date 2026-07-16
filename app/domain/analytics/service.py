from datetime import date
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.models import AnalyticsMetricType
from app.domain.analytics.repository import AnalyticsRepository
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.projections.base import BaseEventProjection


class AnalyticsProjection(BaseEventProjection):
    """
    Projection responsible for maintaining analytics read models.
    Translates raw business events into aggregated metrics.
    """
    @property
    def name(self) -> str:
        return "AnalyticsProjection"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Aggregates raw business events into daily business metrics."

    @property
    def subscribed_categories(self) -> List[EventCategory]:
        return [
            EventCategory.CONVERSATION,
            EventCategory.SCHEDULING,
            EventCategory.FOLLOWUP,
            EventCategory.LEAD,
        ]

    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    async def project_event(self, event: UniversalBaseEvent, session: AsyncSession, **kwargs: Any) -> None:
        """
        Extracts metrics from the event and updates the analytics read model.
        """
        # Determine the date bucket based on event occurrence
        metric_date = event.occurred_at.date()
        
        # Route logic based on event type
        if event.category == EventCategory.CONVERSATION:
            if event.event_name == "customer.replied":
                await self.repository.increment_metric(
                    session, event.workspace_id, "customer", event.customer_id, 
                    metric_date, AnalyticsMetricType.CUSTOMER_REPLIES
                )
                await self.repository.increment_metric(
                    session, event.workspace_id, "workspace", event.workspace_id, 
                    metric_date, AnalyticsMetricType.CUSTOMER_REPLIES
                )
        
        elif event.category == EventCategory.SCHEDULING:
            if event.event_name == "MeetingBookedEvent":
                await self.repository.increment_metric(
                    session, event.workspace_id, "workspace", event.workspace_id,
                    metric_date, AnalyticsMetricType.MEETINGS_SCHEDULED
                )
                if event.customer_id:
                    await self.repository.increment_metric(
                        session, event.workspace_id, "customer", event.customer_id,
                        metric_date, AnalyticsMetricType.MEETINGS_SCHEDULED
                    )


class AnalyticsQueryService:
    """
    Query service that retrieves metrics from the Analytics read model.
    """
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    async def get_workspace_metrics(
        self, session: AsyncSession, workspace_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Any]:
        return await self.repository.get_metrics(
            session, workspace_id, target_type="workspace", target_id=workspace_id, start_date=start_date, end_date=end_date
        )

    async def get_customer_metrics(
        self, session: AsyncSession, workspace_id: UUID, customer_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Any]:
        return await self.repository.get_metrics(
            session, workspace_id, target_type="customer", target_id=customer_id, start_date=start_date, end_date=end_date
        )
