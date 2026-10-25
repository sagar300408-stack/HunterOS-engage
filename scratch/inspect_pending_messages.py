import asyncio
from sqlalchemy import select
from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord

async def main():
    async with get_session() as s:
        stmt = select(EventRecord).where(
            EventRecord.event_name.in_(["MessageReadyToSendEvent", "MessageReceived"]),
            EventRecord.lifecycle_state.in_(["PERSISTED", "QUEUED", "PROCESSING", "RETRYING"])
        )
        res = await s.execute(stmt)
        records = res.scalars().all()
        print(f"Found {len(records)} pending MessageReadyToSendEvent / MessageReceived records:")
        for r in records:
            payload = r.payload or {}
            print(f"ID={r.event_id} name={r.event_name} state={r.lifecycle_state} to_phone={payload.get('to_phone') or payload.get('from_phone')} retries={r.retry_count} occurred={r.occurred_at}")

if __name__ == "__main__":
    asyncio.run(main())
