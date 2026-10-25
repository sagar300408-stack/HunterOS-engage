import asyncio
import json
import uuid
from sqlalchemy import select
from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.domain.conversations.models import Message
from app.domain.timeline.models import TimelineEntry

async def inspect():
    event_id = uuid.UUID("d0f54817-b0fe-440c-bb88-0d96477cc40f")
    correlation_id = uuid.UUID("2d125546-cfc2-4410-ac0a-364d876ec3d4")
    msg_id = uuid.UUID("7e37fa4e-fce1-43bf-82b8-800928014c08")
    expected_action_id = uuid.UUID("8b3f4225-ffb2-4b46-ba34-028ce83ba966")

    print("=" * 70)
    print("DETAILED PIPELINE AUDIT EVIDENCE")
    print("=" * 70)

    async with get_session() as s:
        # 1. Inspect EventRecord
        ev = await s.get(EventRecord, event_id)
        print(f"1. EventRecord ({event_id}):")
        if ev:
            print(f"   Name: {ev.event_name}")
            print(f"   Lifecycle State: {ev.lifecycle_state}")
            print(f"   Retry Count: {ev.retry_count}")
            print(f"   Occurred At: {ev.occurred_at}")
            print(f"   Queued At: {ev.queued_at}")
            print(f"   Processing Started At: {ev.processing_started_at}")
            print(f"   Completed At: {ev.completed_at}")
            print(f"   Error Detail: {ev.error_detail}")
            meta = ev.metadata_payload or {}
            print(f"   Completed Consumers: {meta.get('completed_consumers')}")
            spans = meta.get('consumer_spans', [])
            print(f"   Consumer Spans ({len(spans)}):")
            for sp in spans:
                print(f"     - {sp.get('consumer')}: status={sp.get('status')} duration={sp.get('duration_ms')}ms error={sp.get('exception_msg')}")
        else:
            print("   NOT FOUND")

        # 2. Inspect Message
        msg = await s.get(Message, msg_id)
        print(f"\n2. Message Row ({msg_id}):")
        if msg:
            print(f"   Direction: {msg.direction}")
            print(f"   Content: {msg.content}")
            print(f"   wa_message_id: {msg.wa_message_id}")
            print(f"   Timestamp: {msg.timestamp}")
        else:
            print("   NOT FOUND")

        # 3. Inspect ReplySent
        reply_stmt = select(EventRecord).where(
            EventRecord.correlation_id == correlation_id,
            EventRecord.event_name == "ReplySent"
        )
        res = await s.execute(reply_stmt)
        reply = res.scalar_one_or_none()
        print(f"\n3. ReplySent Event:")
        if reply:
            print(f"   Event ID: {reply.event_id}")
            print(f"   State: {reply.lifecycle_state}")
            print(f"   Payload wa_message_id: {reply.payload.get('wa_message_id') if reply.payload else None}")
            print(f"   Occurred At: {reply.occurred_at}")
        else:
            print("   NOT FOUND")

        # 4. Inspect TimelineEntry
        tl_stmt = select(TimelineEntry).where(TimelineEntry.event_id == event_id)
        tl_res = await s.execute(tl_stmt)
        tl = tl_res.scalar_one_or_none()
        print(f"\n4. TimelineEntry Row:")
        if tl:
            print(f"   Timeline ID: {tl.timeline_id}")
            print(f"   Action ID: {tl.action_id} (Expected: {expected_action_id})")
            print(f"   Activity Type: {tl.activity_type}")
            print(f"   Severity: {tl.severity}")
            print(f"   Occurred At: {tl.occurred_at}")
            print(f"   Structured Data: {json.dumps(tl.structured_data)}")
        else:
            print("   NOT FOUND")

if __name__ == "__main__":
    asyncio.run(inspect())
