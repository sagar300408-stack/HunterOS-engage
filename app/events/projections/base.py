from abc import ABC, abstractmethod
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory


class BaseEventProjection(ABC):
    """
    Abstract base class for all HunterOS Projections (Timeline, Analytics, Audit, etc.).
    A projection takes a domain event and produces a read-only materialization of it.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the projection (e.g. 'TimelineProjection')."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the projection (e.g. '1.0.0')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of what this projection builds."""
        pass

    @property
    @abstractmethod
    def subscribed_categories(self) -> List[EventCategory]:
        """The list of event categories this projection cares about."""
        pass

    @abstractmethod
    async def project_event(self, event: UniversalBaseEvent, session: AsyncSession, **kwargs: Any) -> Any:
        """
        Projects an event into the target read model.
        Returns the projected object or None if the event is not relevant.
        """
        pass
