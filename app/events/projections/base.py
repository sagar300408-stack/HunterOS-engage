from abc import ABC, abstractmethod
from typing import Any, Optional

from app.events.model.base_event import UniversalBaseEvent


class BaseEventProjection(ABC):
    """
    Abstract base class for all HunterOS Projections (Timeline, Analytics, Audit, etc.).
    A projection takes a domain event and produces a read-only materialization of it.
    """

    @abstractmethod
    async def project_event(self, event: UniversalBaseEvent, **kwargs: Any) -> Optional[Any]:
        """
        Projects an event into the target read model.
        Returns the projected object or None if the event is not relevant.
        """
        pass
