import asyncio
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from app.config import get_settings
from app.domain.conversations.models import Message, MessageDirection, Conversation
from app.domain.customers.models import Customer
from app.domain.timeline.models import TimelineEntry
from app.events.bus.event_bus import EventBus
from app.events.dispatcher.poller import OutboxPoller
from app.events.message_events import MessageReadyToSendEvent
from app.events.model.actor_types import ActorType
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService
from app.integrations.postgres.database import get_session, get_session_factory
from app.celery_app import celery_app


async def execute_live_verification():
    print("=" * 70)
    print("HUNTEROS ENGAGE: CONTROLLED LIVE OUTBOUND WHATSAPP VERIFICATION")
    print("=" * 70)

    # 1. Target parameters
    recipient_phone = "919108976764"  # Sagar
    clean_phone_display = "+91...764"
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    customer_id = uuid.UUID("bbe8aa52-068d-4bce-a071-4aec7e7e2cbb")
    conversation_id = uuid.UUID("5d12242d-d836-4671-b090-1eb74550cff9")
    
    correlation_id = uuid.uuid4()
    action_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    token = correlation_id.hex[:8]

    content = f"HunterOS Engage Live Verification: Outbound delivery and timeline projection verified [{token}]."

    print(f"[STAGE 1] Preparing outbound message:")
    print(f"  Recipient: {clean_phone_display}")
    print(f"  Workspace ID: {workspace_id}")
    print(f"  Customer ID: {customer_id}")
    print(f"  Conversation ID: {conversation_id}")
    print(f"  Message ID: {msg_id}")
    print(f"  Correlation ID: {correlation_id}")
    print(f"  Action ID: {action_id}")
    print(f"  Content: {content}")

    # 2. Persist Message and MessageReadyToSendEvent into Transactional Outbox
    ready_event_id = None
    async with get_session() as session:
        # Create outgoing Message row
        outgoing_msg = Message(
            id=msg_id,
            conversation_id=conversation_id,
            direction=MessageDirection.outgoing,
            content=content,
            wa_message_id=None,
            timestamp=datetime.now(timezone.utc),
        )
        session.add(outgoing_msg)

        # Create MessageReadyToSendEvent
        ready_event = MessageReadyToSendEvent(
            to_phone=f"+{recipient_phone}",
            content=content,
            conversation_id=str(conversation_id),
            workspace_id=workspace_id,
            customer_id=customer_id,
            actor_type=ActorType.SYSTEM,
            correlation_id=correlation_id,
            causation_id=correlation_id,
            metadata={
                "message_id": str(msg_id),
                "action_id": str(action_id),
            },
        )
        ready_event_id = ready_event.event_id

        local_bus = EventBus(EventStoreService(EventStoreRepository()))
        await local_bus.publish(session, ready_event)
        await session.commit()

    print(f"\n[STAGE 2] Outbox Event Persisted:")
    print(f"  Event ID: {ready_event_id}")
    print(f"  State in DB: PERSISTED")

    # 3. Start Celery Worker (Solo Pool)
    print(f"\n[STAGE 3] Starting Celery Solo Worker...")
    worker_cmd = [
        sys.executable,
        "-m", "celery",
        "-A", "app.celery_app",
        "worker",
        "-Q", "event_dispatch,celery",
        "--pool=solo",
        "-l", "info",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    worker_proc = subprocess.Popen(
        worker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    # Give the worker a moment to bootstrap and connect to Redis
    time.sleep(3)

    try:
        # 4. Outbox Dispatcher Cycle
        print(f"\n[STAGE 4] Executing Outbox Poller dispatch cycle...")
        poller = OutboxPoller(
            session_factory=get_session_factory(),
            celery_app=celery_app,
        )
        await poller.poll_and_dispatch()
        print("  Poller cycle complete: Event moved to QUEUED and dispatched to Celery.")

        # 5. Wait for Celery Worker to process the event
        print(f"\n[STAGE 5] Waiting for Celery worker processing...")
        max_wait = 25
        start_wait = time.monotonic()
        final_record = None

        while time.monotonic() - start_wait < max_wait:
            await asyncio.sleep(1)
            async with get_session() as session:
                rec = await session.get(EventRecord, ready_event_id)
                if rec and rec.lifecycle_state in ("COMPLETED", "DEAD_LETTER"):
                    final_record = rec
                    break
                elif rec and rec.lifecycle_state == "RETRYING":
                    final_record = rec
                    print(f"  Warning: Event transitioned to RETRYING (retry_count={rec.retry_count})")
                    break

        if not final_record:
            async with get_session() as session:
                final_record = await session.get(EventRecord, ready_event_id)

    finally:
        print(f"\n[STAGE 6] Stopping Celery Solo Worker...")
        worker_proc.terminate()
        stdout, stderr = "", ""
        try:
            stdout, stderr = worker_proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
            stdout, stderr = worker_proc.communicate()
        print("  Celery worker stopped.")
        if stderr and ("ERROR" in stderr or "Traceback" in stderr):
            print(f"Worker stderr sample:\n{stderr[-1500:]}")

    # 7. Verification and Audit Collection
    print("\n" + "=" * 70)
    print("VERIFICATION OF PIPELINE RESULTS")
    print("=" * 70)

    if not final_record:
        print("ERROR: EventRecord not found in database!")
        return

    print(f"Event Lifecycle State: {final_record.lifecycle_state}")
    print(f"Retry Count: {final_record.retry_count}")
    print(f"Queued At: {final_record.queued_at}")
    print(f"Processing Started At: {final_record.processing_started_at}")
    print(f"Completed At: {final_record.completed_at}")
    print(f"Error Detail: {final_record.error_detail}")

    meta = final_record.metadata_payload or {}
    completed_consumers = meta.get("completed_consumers", [])
    print(f"Completed Consumers: {completed_consumers}")

    spans = meta.get("consumer_spans", [])
    print(f"\nConsumer Spans ({len(spans)}):")
    for s in spans:
        print(f"  - {s.get('consumer')}: status={s.get('status')} duration={s.get('duration_ms')}ms error={s.get('exception_msg')}")

    # Inspect Message row
    async with get_session() as session:
        msg_db = await session.get(Message, msg_id)
        wa_message_id = msg_db.wa_message_id if msg_db else None
        print(f"\nDatabase Message Row:")
        print(f"  ID: {msg_db.id if msg_db else 'NOT FOUND'}")
        print(f"  wa_message_id: {wa_message_id}")

        # Inspect ReplySent event
        reply_stmt = select(EventRecord).where(
            EventRecord.correlation_id == correlation_id,
            EventRecord.event_name == "ReplySent",
        )
        reply_res = await session.execute(reply_stmt)
        reply_record = reply_res.scalar_one_or_none()
        print(f"\nReplySent EventRecord:")
        if reply_record:
            print(f"  ID: {reply_record.event_id}")
            print(f"  State: {reply_record.lifecycle_state}")
            print(f"  Payload wa_message_id: {reply_record.payload.get('wa_message_id') if reply_record.payload else None}")
        else:
            print("  NOT FOUND")

        # Inspect TimelineEntry
        tl_stmt = select(TimelineEntry).where(
            TimelineEntry.event_id == ready_event_id
        )
        tl_res = await session.execute(tl_stmt)
        tl_entry = tl_res.scalar_one_or_none()
        print(f"\nTimelineEntry Row:")
        if tl_entry:
            print(f"  Timeline ID: {tl_entry.timeline_id}")
            print(f"  Action ID: {tl_entry.action_id} (Expected: {action_id})")
            print(f"  Activity Type: {tl_entry.activity_type}")
            print(f"  Occurred At: {tl_entry.occurred_at}")
        else:
            print("  NOT FOUND")

    print("\n" + "=" * 70)
    success = (
        final_record.lifecycle_state == "COMPLETED"
        and wa_message_id is not None
        and "WhatsAppSendConsumer" in completed_consumers
        and tl_entry is not None
        and tl_entry.action_id == action_id
    )
    if success:
        print("OVERALL LIVE VERIFICATION RESULT: PASS")
    else:
        print("OVERALL LIVE VERIFICATION RESULT: FAIL")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(execute_live_verification())
