import asyncio
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.domain.conversations.models import Message, MessageDirection
from app.domain.timeline.models import TimelineEntry
from app.utils.helpers import normalize_phone

async def monitor(timeout_seconds: int = 120):
    authorized_phone = "919108976764"
    start_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    
    print("=" * 70)
    print("HUNTEROS ENGAGE: LIVE ROUND-TRIP MONITOR ACTIVE")
    print(f"Listening for inbound 'hi' from authorized recipient: +{authorized_phone}")
    print(f"Start window: {start_time.isoformat()}")
    print("=" * 70)

    inbound_message = None
    inbound_event = None
    ai_event = None
    ready_event = None
    reply_event = None
    delivery_status_event = None

    start_mono = time.monotonic()
    last_print = 0

    while time.monotonic() - start_mono < timeout_seconds:
        elapsed = int(time.monotonic() - start_mono)
        if elapsed - last_print >= 5:
            last_print = elapsed
            print(f"[{elapsed}s / {timeout_seconds}s] Waiting for inbound webhook / tracking pipeline...")

        async with get_session() as session:
            # 1. Check for incoming Message
            if not inbound_message:
                msg_stmt = (
                    select(Message)
                    .where(
                        Message.direction == MessageDirection.incoming,
                        Message.timestamp >= start_time,
                    )
                    .order_by(Message.timestamp.desc())
                    .limit(1)
                )
                res = await session.execute(msg_stmt)
                m = res.scalar_one_or_none()
                if m:
                    inbound_message = m
                    print(f"\n[STAGE 1 - INBOUND MESSAGE DETECTED]")
                    print(f"  Message ID: {m.id}")
                    print(f"  Conversation ID: {m.conversation_id}")
                    print(f"  Content: {repr(m.content)}")
                    print(f"  wa_message_id (Inbound): {m.wa_message_id}")
                    print(f"  Timestamp: {m.timestamp}")

            # 2. Check for MessageReceived Event
            if inbound_message and not inbound_event:
                ev_stmt = (
                    select(EventRecord)
                    .where(
                        EventRecord.event_name == "MessageReceived",
                        EventRecord.occurred_at >= start_time,
                    )
                    .order_by(EventRecord.occurred_at.desc())
                    .limit(1)
                )
                res = await session.execute(ev_stmt)
                e = res.scalar_one_or_none()
                if e:
                    inbound_event = e
                    print(f"\n[STAGE 2 - MessageReceived OUTBOX EVENT]")
                    print(f"  Event ID: {e.event_id}")
                    print(f"  Lifecycle State: {e.lifecycle_state}")
                    print(f"  Correlation ID: {e.correlation_id}")

            # 3. Check for AIResponded Event
            if inbound_message and not ai_event:
                ai_stmt = (
                    select(EventRecord)
                    .where(
                        EventRecord.event_name == "AIResponded",
                        EventRecord.occurred_at >= start_time,
                    )
                    .order_by(EventRecord.occurred_at.desc())
                    .limit(1)
                )
                res = await session.execute(ai_stmt)
                ai_e = res.scalar_one_or_none()
                if ai_e:
                    ai_event = ai_e
                    payload = ai_e.payload or {}
                    print(f"\n[STAGE 3 - AIResponded OUTBOX EVENT]")
                    print(f"  Event ID: {ai_e.event_id}")
                    print(f"  Lifecycle State: {ai_e.lifecycle_state}")
                    print(f"  Generated Content: {repr(payload.get('response_content'))}")

            # 4. Check for MessageReadyToSendEvent
            if inbound_message and not ready_event:
                r_stmt = (
                    select(EventRecord)
                    .where(
                        EventRecord.event_name == "MessageReadyToSendEvent",
                        EventRecord.occurred_at >= start_time,
                    )
                    .order_by(EventRecord.occurred_at.desc())
                    .limit(1)
                )
                res = await session.execute(r_stmt)
                re = res.scalar_one_or_none()
                if re:
                    ready_event = re
                    payload = re.payload or {}
                    print(f"\n[STAGE 4 - MessageReadyToSendEvent OUTBOX EVENT]")
                    print(f"  Event ID: {re.event_id}")
                    print(f"  Lifecycle State: {re.lifecycle_state}")
                    print(f"  Target Phone: {payload.get('to_phone')}")
                    print(f"  Content: {repr(payload.get('content'))}")

            # 5. Check for Outbound Message row & ReplySent Event
            if ready_event and not reply_event:
                rep_stmt = (
                    select(EventRecord)
                    .where(
                        EventRecord.event_name == "ReplySent",
                        EventRecord.occurred_at >= start_time,
                    )
                    .order_by(EventRecord.occurred_at.desc())
                    .limit(1)
                )
                res = await session.execute(rep_stmt)
                rep = res.scalar_one_or_none()
                if rep:
                    reply_event = rep
                    payload = rep.payload or {}
                    out_wa_id = payload.get("wa_message_id")
                    print(f"\n[STAGE 5 - ReplySent CONFIRMED (SUBMITTED TO META)]")
                    print(f"  Event ID: {rep.event_id}")
                    print(f"  Provider Message ID (wa_message_id): {out_wa_id}")
                    print(f"  Content: {repr(payload.get('content'))}")

            # 6. Check for Delivery Status webhook
            if reply_event and not delivery_status_event:
                stat_stmt = (
                    select(EventRecord)
                    .where(
                        EventRecord.event_name == "RawWebhookEvent",
                        EventRecord.occurred_at >= start_time,
                    )
                    .order_by(EventRecord.occurred_at.desc())
                )
                res = await session.execute(stat_stmt)
                raw_events = res.scalars().all()
                for rw in raw_events:
                    rw_payload = rw.payload or {}
                    # check if statuses in changes
                    try:
                        changes = rw_payload.get("entry", [{}])[0].get("changes", [{}])[0]
                        val = changes.get("value", {})
                        if "statuses" in val:
                            st = val["statuses"][0]
                            delivery_status_event = st
                            print(f"\n[STAGE 6 - DELIVERY STATUS WEBHOOK RECEIVED FROM META]")
                            print(f"  Status: {st.get('status')}")
                            print(f"  Status Timestamp: {st.get('timestamp')}")
                            print(f"  Meta Message ID: {st.get('id')}")
                            print(f"  Recipient ID: {st.get('recipient_id')}")
                            break
                    except Exception:
                        pass

            # If reply has been sent and terminal state reached, wait briefly for status then finish
            if reply_event:
                # Check ready_event terminal state
                re_refreshed = await session.get(EventRecord, ready_event.event_id)
                if re_refreshed and re_refreshed.lifecycle_state in ("COMPLETED", "DEAD_LETTER"):
                    ready_event = re_refreshed
                    # Wait up to 10 more seconds for delivery status if not yet received
                    if not delivery_status_event and time.monotonic() - start_mono < timeout_seconds - 10:
                        await asyncio.sleep(2)
                        continue
                    break

        await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print("LIVE ROUND-TRIP RESULTS AUDIT SUMMARY")
    print("=" * 70)

    if inbound_message:
        print(f"1. Inbound Message:")
        print(f"   - Message ID: {inbound_message.id}")
        print(f"   - wa_message_id: {inbound_message.wa_message_id}")
        print(f"   - Content: {repr(inbound_message.content)}")
        print(f"   - Timestamp: {inbound_message.timestamp}")
    else:
        print("1. Inbound Message: NOT RECEIVED (Timed out or blocked)")

    if ready_event:
        print(f"\n2. Outbound MessageReadyToSendEvent:")
        print(f"   - Event ID: {ready_event.event_id}")
        print(f"   - Lifecycle State: {ready_event.lifecycle_state}")
        print(f"   - Retry Count: {ready_event.retry_count}")
        meta = ready_event.metadata_payload or {}
        print(f"   - Completed Consumers: {meta.get('completed_consumers')}")
    else:
        print("\n2. Outbound MessageReadyToSendEvent: NOT GENERATED")

    if reply_event:
        payload = reply_event.payload or {}
        print(f"\n3. Meta Submission Result:")
        print(f"   - Event ID: {reply_event.event_id}")
        print(f"   - Provider wa_message_id: {payload.get('wa_message_id')}")
        print(f"   - Content Delivered: {repr(payload.get('content'))}")
    else:
        print("\n3. Meta Submission Result: NOT COMPLETED")

    if delivery_status_event:
        print(f"\n4. Meta Delivery Status Webhook:")
        print(f"   - Status: {delivery_status_event.get('status')}")
        print(f"   - Recipient: {delivery_status_event.get('recipient_id')}")
        print(f"   - Provider Message ID: {delivery_status_event.get('id')}")
    else:
        print("\n4. Meta Delivery Status Webhook: Pending or Not Yet Received")

    # Duplicate check: count outbound messages in this conversation after start_time
    if inbound_message:
        async with get_session() as session:
            out_stmt = select(Message).where(
                Message.conversation_id == inbound_message.conversation_id,
                Message.direction == MessageDirection.outgoing,
                Message.timestamp >= start_time,
            )
            out_res = await session.execute(out_stmt)
            out_msgs = out_res.scalars().all()
            print(f"\n5. Duplicate Response Check:")
            print(f"   - Total Outgoing Messages created for this test: {len(out_msgs)}")
            for idx, om in enumerate(out_msgs, 1):
                print(f"     [{idx}] ID={om.id} wa_id={om.wa_message_id} content={repr(om.content)}")

    print("=" * 70)

if __name__ == "__main__":
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    asyncio.run(monitor(timeout))
