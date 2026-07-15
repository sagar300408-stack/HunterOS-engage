from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.timeline.models import TimelineEntry


class TimelineRepository:
    async def add_entry(self, session: AsyncSession, entry: TimelineEntry) -> TimelineEntry:
        """
        Adds a new timeline entry to the store. 
        Note: The Timeline is strictly append-only / read-only. No update/delete methods exist here.
        """
        session.add(entry)
        await session.flush()
        return entry

    async def get_timeline(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        customer_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TimelineEntry]:
        """
        Retrieves a timeline for a workspace, optionally filtered by customer or conversation.
        Chronologically ordered by occurred_at DESC, then event_id DESC.
        """
        stmt = select(TimelineEntry).where(TimelineEntry.workspace_id == workspace_id)

        if customer_id:
            stmt = stmt.where(TimelineEntry.customer_id == customer_id)
        if conversation_id:
            stmt = stmt.where(TimelineEntry.conversation_id == conversation_id)

        # Ordering by occurred_at then event_id to ensure deterministic chronological order
        stmt = stmt.order_by(TimelineEntry.occurred_at.desc(), TimelineEntry.event_id.desc())
        
        stmt = stmt.limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
