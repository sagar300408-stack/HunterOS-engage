"""
HunterOS Engage — Memory Unit of Work

Implements the Unit of Work pattern ensuring transactional atomicity across:
  - Aggregate Root state persistence
  - Immutable Version Snapshot creation
  - Timeline Event emission
  - Change Log delta recording
  - Domain Event post-commit dispatching
"""

import abc
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.events.models import BaseMemoryDomainEvent
from app.domain.memory.events.publisher import (
    AbstractMemoryEventPublisher,
    get_memory_event_publisher,
)
from app.domain.memory.models import MemoryConcurrencyConflictError
from sqlalchemy.orm.exc import StaleDataError

logger = logging.getLogger(__name__)


class AbstractMemoryUnitOfWork(abc.ABC):
    """Abstract interface for Memory Unit of Work."""

    session: AsyncSession
    event_publisher: AbstractMemoryEventPublisher

    @abc.abstractmethod
    async def __aenter__(self) -> "AbstractMemoryUnitOfWork":
        raise NotImplementedError

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def enqueue_event(self, event: BaseMemoryDomainEvent) -> None:
        raise NotImplementedError


class MemoryUnitOfWork(AbstractMemoryUnitOfWork):
    """
    SQLAlchemy-backed Unit of Work.
    Guarantees atomic commit or clean rollback with post-commit event dispatch.
    """

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        event_publisher: Optional[AbstractMemoryEventPublisher] = None,
    ):
        self.session = session
        self.event_publisher = event_publisher or get_memory_event_publisher()
        self._enqueued_events: List[BaseMemoryDomainEvent] = []
        self._committed = False

    def begin(self, session: AsyncSession) -> "MemoryUnitOfWork":
        """Binds a session dynamically for context management."""
        self.session = session
        return self

    async def __aenter__(self) -> "MemoryUnitOfWork":
        self._enqueued_events.clear()
        self._committed = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
            logger.warning(
                f"MemoryUnitOfWork transaction rolled back due to error: {exc_val}"
            )
        elif not self._committed:
            # If not explicitly committed, commit now
            await self.commit()

    def enqueue_event(self, event: BaseMemoryDomainEvent) -> None:
        """Buffers a domain event to be dispatched only after successful commit."""
        self._enqueued_events.append(event)

    async def commit(self) -> None:
        """Flushes and commits the active database transaction and publishes queued domain events."""
        if self._committed:
            return
        try:
            await self.session.commit()
        except StaleDataError:
            await self.session.rollback()
            raise MemoryConcurrencyConflictError(
                message="Concurrent update detected. The memory record was modified by another transaction.",
                memory_id="unknown", # We don't have the memory ID easily accessible here, but the exception will handle it.
                expected_revision="unknown",
                actual_revision="unknown"
            )
        self._committed = True

        # Dispatch buffered domain events post-commit
        if self._enqueued_events:
            events_to_dispatch = list(self._enqueued_events)
            self._enqueued_events.clear()
            await self.event_publisher.publish_many(self.session, events_to_dispatch)

    async def rollback(self) -> None:
        """Rolls back the current database transaction and drops uncommitted events."""
        self._enqueued_events.clear()
        await self.session.rollback()
