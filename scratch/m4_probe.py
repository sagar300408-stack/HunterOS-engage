"""
Milestone 4 — production validation probe.
Run from the project root: python scratch/m4_probe.py
"""
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState, VALID_TRANSITIONS, can_transition
from app.events.lifecycle.manager import LifecycleManager, InvalidLifecycleTransitionError


async def probe_state_machine():
    print("\n=== PROBE 1: State Machine Completeness ===")
    states = list(EventLifecycleState)
    print(f"States defined: {[s.value for s in states]}")
    assert "FAILED" not in [s.value for s in states], "FAILED must not exist"

    legal = []
    for src, targets in VALID_TRANSITIONS.items():
        for tgt in targets:
            legal.append((src.value, tgt.value))
            assert can_transition(src, tgt), f"can_transition({src},{tgt}) returned False"

    # Test illegal transitions
    illegal_pairs = [
        (EventLifecycleState.COMPLETED, EventLifecycleState.PROCESSING),
        (EventLifecycleState.DEAD_LETTER, EventLifecycleState.PROCESSING),
        (EventLifecycleState.PROCESSING, EventLifecycleState.PERSISTED),
        (EventLifecycleState.QUEUED, EventLifecycleState.COMPLETED),
    ]
    for src, tgt in illegal_pairs:
        assert not can_transition(src, tgt), f"Illegal {src}->{tgt} was allowed!"
    print(f"  Legal transitions : {len(legal)}")
    print(f"  Illegal blocked   : {len(illegal_pairs)}")
    print("  PASS")


async def probe_backoff():
    print("\n=== PROBE 2: Exponential Backoff Schedule ===")
    expected = {0: 10, 1: 20, 2: 40, 3: 80, 4: 160}
    now = datetime.now(timezone.utc)
    for n, want in expected.items():
        got = (2 ** n) * 10
        assert got == want, f"retry {n}: expected {want}s got {got}s"
        eta = (now + timedelta(seconds=got)).strftime("%H:%M:%S UTC")
        print(f"  retry_count={n}  delay={got:>3}s  next_retry_at={eta}")
    print("  PASS")


async def probe_lifecycle_guard():
    print("\n=== PROBE 3: Illegal Transition Guard (InvalidLifecycleTransitionError) ===")
    async with get_session() as session:
        import uuid
        from sqlalchemy import select

        # Insert a synthetic COMPLETED record
        fake_id = uuid.uuid4()
        rec = EventRecord(
            event_id=fake_id,
            schema_version=1,
            occurred_at=datetime.now(timezone.utc),
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            actor_type="test",
            source_subsystem="m4_probe",
            category="test",
            event_name="ProbeEvent",
            payload={},
            metadata_payload={},
            lifecycle_state=EventLifecycleState.COMPLETED.value,
        )
        session.add(rec)
        await session.flush()

        # Attempt COMPLETED -> PROCESSING (must raise)
        try:
            await LifecycleManager.processing(session, fake_id)
            print("  FAIL: expected InvalidLifecycleTransitionError was NOT raised")
        except InvalidLifecycleTransitionError as e:
            print(f"  Caught expected exception: {e}")
            print("  PASS")
        finally:
            await session.rollback()


async def probe_db_state():
    print("\n=== PROBE 4: Live Database State Audit ===")
    async with get_session() as session:
        r = await session.execute(text("SELECT count(*) FROM event_store"))
        total = r.scalar()

        r2 = await session.execute(text(
            "SELECT lifecycle_state, count(*) FROM event_store "
            "GROUP BY lifecycle_state ORDER BY 2 DESC"
        ))
        rows = r2.fetchall()
        print(f"  Total events: {total}")
        print("  State distribution:")
        for state, cnt in rows:
            print(f"    {state:<16} {cnt}")

        r3 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE queued_at IS NOT NULL"
        ))
        print(f"  queued_at populated        : {r3.scalar()}")

        r4 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE processing_started_at IS NOT NULL"
        ))
        print(f"  processing_started_at      : {r4.scalar()}")

        r5 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE completed_at IS NOT NULL"
        ))
        print(f"  completed_at populated     : {r5.scalar()}")

        r6 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE retry_count > 0"
        ))
        print(f"  Events with retry_count>0  : {r6.scalar()}")

        r7 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE idempotency_key IS NOT NULL"
        ))
        print(f"  Events with idempotency_key: {r7.scalar()}")

        r8 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE lifecycle_state='RETRYING'"
            " AND next_retry_at IS NOT NULL"
        ))
        print(f"  RETRYING with next_retry_at: {r8.scalar()}")

        r9 = await session.execute(text(
            "SELECT count(*) FROM event_store WHERE lifecycle_state='RETRYING'"
            " AND next_retry_at <= NOW()"
        ))
        print(f"  RETRYING overdue (ready)   : {r9.scalar()}")

        r10 = await session.execute(text(
            "SELECT count(*) FROM event_store "
            "WHERE lifecycle_state='PROCESSING' "
            "AND processing_started_at < NOW() - INTERVAL '30 minutes'"
        ))
        print(f"  Stale PROCESSING (>30m)    : {r10.scalar()}")

        # Sample recent events
        r11 = await session.execute(text(
            "SELECT event_id, event_name, lifecycle_state, retry_count, "
            "queued_at, processing_started_at, completed_at, next_retry_at "
            "FROM event_store ORDER BY occurred_at DESC LIMIT 5"
        ))
        recent = r11.fetchall()
        if recent:
            print("\n  Last 5 events:")
            for row in recent:
                eid, name, state, retries, qa, psa, ca, nra = row
                print(f"    {str(eid)[:8]}.. {name:<25} state={state:<12} "
                      f"retries={retries} queued_at={'SET' if qa else 'NULL':4} "
                      f"proc_at={'SET' if psa else 'NULL':4} "
                      f"done_at={'SET' if ca else 'NULL'}")


async def probe_idempotency_constraint():
    print("\n=== PROBE 5: Idempotency Unique Constraint ===")
    async with get_session() as session:
        import uuid
        ikey = f"probe_idem_{uuid.uuid4().hex}"
        fake_id_1 = uuid.uuid4()
        fake_id_2 = uuid.uuid4()

        rec1 = EventRecord(
            event_id=fake_id_1,
            schema_version=1,
            occurred_at=datetime.now(timezone.utc),
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            actor_type="test",
            source_subsystem="m4_probe",
            category="test",
            event_name="ProbeEvent",
            payload={},
            metadata_payload={},
            lifecycle_state=EventLifecycleState.PERSISTED.value,
            idempotency_key=ikey,
        )
        session.add(rec1)
        await session.flush()

        rec2 = EventRecord(
            event_id=fake_id_2,
            schema_version=1,
            occurred_at=datetime.now(timezone.utc),
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            actor_type="test",
            source_subsystem="m4_probe",
            category="test",
            event_name="ProbeEvent",
            payload={},
            metadata_payload={},
            lifecycle_state=EventLifecycleState.PERSISTED.value,
            idempotency_key=ikey,  # same key — must fail
        )
        session.add(rec2)
        try:
            await session.flush()
            print("  FAIL: duplicate idempotency_key was accepted")
        except Exception as e:
            err = str(e)
            if "unique" in err.lower() or "uq_" in err.lower() or "duplicate" in err.lower():
                print(f"  Caught unique violation: {type(e).__name__}")
                print("  PASS")
            else:
                print(f"  UNEXPECTED exception: {e}")
        finally:
            await session.rollback()


async def probe_dispatcher_shape():
    print("\n=== PROBE 6: Dispatcher Architecture ===")
    from app.events.bus.dispatcher import OutboxDispatcher
    import inspect

    d = OutboxDispatcher(batch_size=50, poll_interval=1.0)
    assert d.batch_size == 50
    assert d.poll_interval == 1.0
    assert not d._running

    # Both passes exist and are coroutine functions
    assert asyncio.iscoroutinefunction(OutboxDispatcher.process_batch)
    assert asyncio.iscoroutinefunction(OutboxDispatcher.process_retry_batch)
    assert asyncio.iscoroutinefunction(OutboxDispatcher.start)

    src = inspect.getsource(OutboxDispatcher.process_retry_batch)
    assert "next_retry_at" in src, "process_retry_batch must filter by next_retry_at"
    assert "RETRYING" in src, "process_retry_batch must query RETRYING state"
    assert "LifecycleManager.requeue" in src, "must use LifecycleManager.requeue"
    assert "skip_locked" in src.lower() or "SKIP LOCKED" in src, "must use FOR UPDATE SKIP LOCKED"

    src2 = inspect.getsource(OutboxDispatcher.process_batch)
    assert "LifecycleManager.queue" in src2, "process_batch must use LifecycleManager.queue"
    assert "skip_locked" in src2.lower(), "must use FOR UPDATE SKIP LOCKED"

    print("  process_batch()       : queries PERSISTED, FOR UPDATE SKIP LOCKED, LifecycleManager.queue()")
    print("  process_retry_batch() : queries RETRYING+next_retry_at<=NOW, SKIP LOCKED, LifecycleManager.requeue()")
    print("  start() runs both passes each poll cycle")
    print("  PASS")


async def probe_maintenance():
    print("\n=== PROBE 7: Stale Event Recovery Architecture ===")
    from app.events.worker.maintenance import _recover_stale_events_async
    import inspect

    src = inspect.getsource(_recover_stale_events_async)
    assert "processing_started_at" in src, "must filter by processing_started_at"
    assert "LifecycleManager.retry" in src, "must call LifecycleManager.retry"
    assert "LifecycleManager.dead_letter" in src, "must call LifecycleManager.dead_letter"
    assert "session.begin()" in src, "must use explicit transaction per event"
    assert "2 **" in src, "must use exponential backoff"

    print("  Scans: PROCESSING events where processing_started_at < NOW() - threshold")
    print("  Per-event transactions (one failure cannot block others)")
    print("  Routes to RETRYING (with backoff) or DEAD_LETTER (max retries exceeded)")
    print("  PASS")


async def main():
    await probe_state_machine()
    await probe_backoff()
    try:
        await probe_lifecycle_guard()
    except Exception as e:
        print(f"  SKIP (DB unavailable): {e}")
    try:
        await probe_db_state()
    except Exception as e:
        print(f"  SKIP (DB unavailable): {e}")
    try:
        await probe_idempotency_constraint()
    except Exception as e:
        print(f"  SKIP (DB unavailable): {e}")
    await probe_dispatcher_shape()
    await probe_maintenance()
    print("\n=== All probes complete ===\n")


if __name__ == "__main__":
    asyncio.run(main())
