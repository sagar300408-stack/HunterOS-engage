"""
HunterOS Engage — Abstract Memory Write Repository (CQRS)

Command interface for persisting state mutations on CustomerMemory Aggregate Root.
"""

import abc
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import CustomerMemory


class AbstractMemoryWriteRepository(abc.ABC):
    """Abstract write repository for Customer Memory aggregate."""

    @abc.abstractmethod
    async def add(self, session: AsyncSession, memory: CustomerMemory) -> CustomerMemory:
        """Persist a new CustomerMemory aggregate."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, session: AsyncSession, memory: CustomerMemory) -> CustomerMemory:
        """Mark memory aggregate as modified."""
        raise NotImplementedError

    @abc.abstractmethod
    async def hard_delete(self, session: AsyncSession, memory: CustomerMemory) -> None:
        """Hard-delete memory aggregate (administrative/testing only)."""
        raise NotImplementedError
