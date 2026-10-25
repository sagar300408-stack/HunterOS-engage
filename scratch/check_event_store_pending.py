import asyncio
from sqlalchemy import select, text
from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord

async def main():
    async with get_session() as s:
        # Check active / pending states
        stmt = select(EventRecord.event_id, EventRecord.event_name, EventRecord.lifecycle_state, EventRecord.retry_count, EventRecord.occurred_at).where(
            EventRecord.lifecycle_state.in_(["PERSISTED", "QUEUED", "PROCESSING", "RETRYING"])
        )
        res = await s.execute(stmt)
        pending = res.fetchall()
        print(f"PENDING_EVENTS_COUNT: {len(pending)}")
        for p in pending:
            print(f"  id={p.event_id} name={p.event_name} state={p.lifecycle_state} retries={p.retry_count} occurred={p.occurred_at}")

        # Also check Redis queues
        import redis
        r = redis.Redis(host="localhost", port=6379, db=1)
        for q in ["celery", "event_dispatch"]:
            llen = r.llen(q)
            print(f"REDIS_QUEUE_LENGTH [{q}]: {llen}")

if __name__ == "__main__":
    asyncio.run(main())
