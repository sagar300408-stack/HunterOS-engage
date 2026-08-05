"""
HunterOS Engage — SQLAlchemy Memory Write Repository (CQRS)

Concrete implementation of AbstractMemoryWriteRepository using async SQLAlchemy.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.interfaces.write_repository import AbstractMemoryWriteRepository
from app.domain.memory.models import CustomerMemory


class SqlAlchemyMemoryWriteRepository(AbstractMemoryWriteRepository):
    """
    SQLAlchemy write repository for CustomerMemory domain.
    """

    async def add(self, session: AsyncSession, memory: CustomerMemory) -> CustomerMemory:
        session.add(memory)
        return memory

    async def update(self, session: AsyncSession, memory: CustomerMemory) -> CustomerMemory:
        # In SQLAlchemy with session tracking, mutating memory marks it dirty.
        # Calling merge/add ensures session attachment.
        session.add(memory)
        return memory

    async def hard_delete(self, session: AsyncSession, memory: CustomerMemory) -> None:
        await session.delete(memory)
