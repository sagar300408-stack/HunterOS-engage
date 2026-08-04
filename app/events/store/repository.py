"""
HunterOS Engage — Event Store Repository
app/events/store/repository.py

Repository for persisting and retrieving events from the immutable Event Store.
Provides savepoint-isolated writes and fast key lookups.
"""

from __future__ import annotations

from typing import Any, List, Optional
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.events.idempotency.decision import IdempotencyConflictError
from app.events.store.models import EventRecord


class EventStoreRepository:
    """
    Repository for persisting and retrieving events from the immutable Event Store.
    """

    async def get_by_idempotency_key(
        self,
        session: AsyncSession,
        idempotency_key: str,
    ) -> Optional[EventRecord]:
        """
        Retrieves an event record by its unique idempotency_key.
        """
        if not idempotency_key:
            return None
        stmt = select(EventRecord).filter(EventRecord.idempotency_key == idempotency_key)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_event_id(
        self,
        session: AsyncSession,
        event_id: Any,
    ) -> Optional[EventRecord]:
        """
        Retrieves an event record by its primary key event_id.
        """
        stmt = select(EventRecord).filter(EventRecord.event_id == event_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def save_event(
        self,
        session: AsyncSession,
        record: EventRecord,
    ) -> EventRecord:
        """
        Persists a new event record within an isolated SAVEPOINT.
        
        If an IntegrityError occurs (e.g. concurrent race condition on the unique
        idempotency_key constraint), the savepoint is rolled back cleanly, and an
        IdempotencyConflictError is raised without aborting the outer transaction.
        """
        try:
            async with session.begin_nested():
                session.add(record)
                await session.flush()
            return record
        except IntegrityError as exc:
            # SAVEPOINT automatically rolled back by context manager
            raise IdempotencyConflictError(
                idempotency_key=record.idempotency_key or "",
                message=f"Unique constraint violation for idempotency_key '{record.idempotency_key}'",
            ) from exc

    async def get_events(
        self,
        session: AsyncSession,
        workspace_id: str,
        limit: int = 100,
        offset: int = 0,
        **filters,
    ) -> List[EventRecord]:
        """
        Basic retrieval of historical events, ordered chronologically.
        Filters allow querying by category, event_name, customer_id, etc.
        """
        stmt = select(EventRecord).filter_by(workspace_id=workspace_id)

        for key, value in filters.items():
            if hasattr(EventRecord, key) and value is not None:
                stmt = stmt.filter(getattr(EventRecord, key) == value)

        stmt = stmt.order_by(desc(EventRecord.occurred_at)).offset(offset).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())
