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
        stmt = insert(EventRecord).values(
            event_id=record.event_id,
            workspace_id=record.workspace_id,
            correlation_id=record.correlation_id,
            causation_id=record.causation_id,
            category=record.category,
            event_name=record.event_name,
            actor_type=record.actor_type,
            source_subsystem=record.source_subsystem,
            occurred_at=record.occurred_at,
            customer_id=record.customer_id,
            payload=record.payload,
            version=record.version,
            lifecycle_state=record.lifecycle_state,
            retry_count=record.retry_count,
            next_retry_at=record.next_retry_at,
            error_detail=record.error_detail,
            priority=record.priority,
            partition_key=record.partition_key,
            trace_id=record.trace_id,
            event_version=record.event_version,
            queued_at=record.queued_at,
            processing_started_at=record.processing_started_at,
            completed_at=record.completed_at,
            idempotency_key=record.idempotency_key
        )
        
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
