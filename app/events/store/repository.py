from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import insert

from app.events.store.models import EventRecord

class EventStoreRepository:
    """
    Repository for persisting and retrieving events from the immutable Event Store.
    """

    async def save_event(self, session: AsyncSession, record: EventRecord) -> None:
        """
        Persists a new event record using an upsert with DO NOTHING on conflict
        to enforce idempotency based on the idempotency_key.
        This is an append-only operation.
        """
        values = {}
        for column in EventRecord.__table__.columns:
            val = getattr(record, column.name)
            if val is not None:
                values[column.name] = val
                
        stmt = insert(EventRecord).values(**values)
        
        stmt = stmt.on_conflict_do_nothing(index_elements=['idempotency_key'])
        
        await session.execute(stmt)
        await session.flush()

    async def get_events(
        self,
        session: AsyncSession,
        workspace_id: str,
        limit: int = 100,
        offset: int = 0,
        **filters
    ):
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
        return result.scalars().all()
