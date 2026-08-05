"""
HunterOS Engage — Memory Domain Event Publisher

Publishes memory domain events to the platform EventBus / Transactional Outbox.
Strictly publish-only (no consumers implemented in memory foundation).
"""

import abc
import logging
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.events.models import BaseMemoryDomainEvent
from app.events.bus.interfaces import EventPublisher

logger = logging.getLogger(__name__)


class AbstractMemoryEventPublisher(abc.ABC):
    """Abstract interface for publishing domain events originating from Memory domain."""

    @abc.abstractmethod
    async def publish(self, session: Optional[AsyncSession], event: BaseMemoryDomainEvent) -> None:
        """Publish a single domain event."""
        raise NotImplementedError

    @abc.abstractmethod
    async def publish_many(
        self, session: Optional[AsyncSession], events: List[BaseMemoryDomainEvent]
    ) -> None:
        """Publish a list of domain events."""
        raise NotImplementedError


class MemoryEventPublisher(AbstractMemoryEventPublisher):
    """
    Standard memory event publisher.
    Delegates to platform EventBus if available, or logs events gracefully.
    """

    def __init__(self, platform_event_bus: Optional[EventPublisher] = None):
        self._platform_event_bus = platform_event_bus
        self._published_events: List[BaseMemoryDomainEvent] = []

    async def publish(self, session: Optional[AsyncSession], event: BaseMemoryDomainEvent) -> None:
        """Publish a single domain event."""
        self._published_events.append(event)

        logger.info(
            "memory_domain_event_published",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "aggregate_id": str(event.aggregate_id),
                "tenant_id": str(event.tenant_id) if event.tenant_id else None,
                "version": event.version,
            },
        )

        if self._platform_event_bus is not None and session is not None:
            try:
                await self._platform_event_bus.publish(session, event)
            except Exception as exc:
                logger.warning(
                    f"Platform event bus publication deferred/failed: {exc}. Memory event stored in domain publisher buffer."
                )

    async def publish_many(
        self, session: Optional[AsyncSession], events: List[BaseMemoryDomainEvent]
    ) -> None:
        """Publish multiple domain events."""
        for event in events:
            await self.publish(session, event)

    def get_published_events(self) -> List[BaseMemoryDomainEvent]:
        """Returns the in-memory log of published events (primarily for testing and auditing)."""
        return list(self._published_events)

    def clear(self) -> None:
        """Clears the published events buffer."""
        self._published_events.clear()


# Alias for in-memory testing
InMemoryMemoryEventPublisher = MemoryEventPublisher

# Default singleton instance
_default_publisher: Optional[MemoryEventPublisher] = None


def get_memory_event_publisher(bus: Optional[EventPublisher] = None) -> MemoryEventPublisher:
    """Factory helper to obtain the memory domain event publisher."""
    global _default_publisher
    if _default_publisher is None or bus is not None:
        _default_publisher = MemoryEventPublisher(platform_event_bus=bus)
    return _default_publisher
