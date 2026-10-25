import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord

async def main():
    async with get_session() as s:
        # Find all pending events in event_store
        stmt = select(EventRecord).where(
            EventRecord.lifecycle_state.in_(["PERSISTED", "QUEUED", "PROCESSING", "RETRYING"])
        )
        res = await s.execute(stmt)
        records = res.scalars().all()
        print(f"Clearing {len(records)} stale backlog records before live test...")
        for r in records:
            r.lifecycle_state = "DEAD_LETTER"
            r.error_detail = "stale_backlog_cleared_preflight: archived before controlled live test"
            r.completed_at = datetime.now(timezone.utc)
        await s.commit()
        print("All stale backlog events transitioned to DEAD_LETTER.")

if __name__ == "__main__":
    asyncio.run(main())
