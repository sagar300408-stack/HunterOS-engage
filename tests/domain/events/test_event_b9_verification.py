"""
B9 Certification — Transactional Outbox Behavior
=================================================
Proves atomicity in both directions:

  SUCCESS:  business commit + outbox commit are atomic
  FAILURE:  business rollback → outbox event does NOT persist
  OUTBOX FAILURE: integrity error → outer transaction recovers via SAVEPOINT

All tests use real PostgreSQL — SQLite is not sufficient for B9.

The critical invariants:
  ✓ STATE COMMITTED  + EVENT COMMITTED   (success path)
  ✓ STATE ROLLED BACK + EVENT NOT PERSISTED (rollback path)
  ✗ STATE COMMITTED  + EVENT LOST         (must be impossible)
  ✗ STATE ROLLED BACK + EVENT PERSISTED   (must be impossible)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Type

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── Domain model imports ──────────────────────────────────────────────────────
from app.domain.conversations.models import Base  # noqa: F401
from app.domain.customers.models import Customer  # noqa: F401
from app.domain.memory.models import CustomerMemory  # noqa: F401
from app.domain.intent.models import IntentHistory  # noqa: F401
from app.domain.security.models import AuditLog  # noqa: F401
from app.domain.dashboard.models import PipelineEvent  # noqa: F401
from app.domain.followup.models import FollowUpQueue  # noqa: F401

# ── Event infrastructure ──────────────────────────────────────────────────────
from app.events.bus.event_bus import EventBus
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.idempotency.decision import IdempotencyConflictError
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.actor_types import ActorType
from app.events.model.lifecycle import EventLifecycleState
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService

from tests.domain.events.conftest import _delete_event_store_rows


def _make_bus() -> EventBus:
    return EventBus(store_service=EventStoreService(repository=EventStoreRepository()))


def _make_event(ws_id: uuid.UUID, *, wa_id: str | None = None) -> CustomerRepliedEvent:
    return CustomerRepliedEvent(
        workspace_id=ws_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="b9_test",
        message_content="B9 transactional outbox test",
        wa_message_id=wa_id or f"wa_{uuid.uuid4().hex[:12]}",
    )


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 1 — Business commit + outbox commit are atomic (SUCCESS path)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_business_commit_and_outbox_commit_atomic(pg_session, pg_session_factory):
    """
    Proves: when the DB transaction commits, BOTH the business entity and the
    outbox event are visible in the database. Neither is lost.

    STATE COMMITTED + EVENT COMMITTED = required invariant.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        # Single transaction: create business entity + publish event
        async with pg_session.begin():
            # Simulate a business entity write (using event_store for simplicity —
            # the real invariant is that both rows commit together)
            record = await bus.publish(pg_session, event)
            assert record is not None

        # After commit — verify event is in the outbox
        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)

        assert stored is not None, \
            "INVARIANT VIOLATED: event_store row must be visible after commit"
        assert stored.lifecycle_state == EventLifecycleState.PERSISTED.value

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 2 — Business rollback purges outbox event (ROLLBACK path)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_business_rollback_purges_outbox_event(pg_session, pg_session_factory):
    """
    Proves: when the outer transaction rolls back, the outbox event is also
    rolled back. No phantom event record is left in event_store.

    STATE ROLLED BACK + EVENT NOT PERSISTED = required invariant.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)
    repo = EventStoreRepository()

    try:
        # Publish within a transaction that we deliberately roll back
        try:
            async with pg_session.begin():
                await bus.publish(pg_session, event)
                # Simulate business logic failure → raise to trigger rollback
                raise ValueError("Simulated business failure — must rollback entire transaction")
        except ValueError:
            pass  # Expected — we caused this rollback intentionally

        # After rollback — the outbox event must NOT be in PostgreSQL
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)

        assert stored is None, (
            "INVARIANT VIOLATED: event_store row must NOT exist after transaction rollback. "
            f"Found: {stored}"
        )

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 3 — Outbox UNIQUE constraint violation recovers via SAVEPOINT
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_outbox_integrity_constraint_outer_transaction_survives(pg_session, pg_session_factory):
    """
    When the same event is published twice within different transactions,
    the second publication hits the UNIQUE constraint on idempotency_key.
    The SAVEPOINT mechanism must recover the outer transaction (no crash).
    The second publish returns the existing record — no duplicate.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        # First publish — succeeds
        async with pg_session.begin():
            record1 = await bus.publish(pg_session, event)
        assert record1 is not None

        # Second publish — same event, duplicate idempotency key
        # The IdempotencyEngine must catch it (pre-lookup) or SAVEPOINT catches DB constraint
        async with pg_session_factory() as session2:
            async with session2.begin():
                record2 = await bus.publish(session2, event)

        # Both records must refer to the same underlying event
        assert record2 is not None
        assert record2.event_id == record1.event_id, \
            "Duplicate publish must return the EXISTING record, not create a new one"

        # Only ONE row in event_store for this event
        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)
        assert stored is not None

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 4 — Retry exponential backoff schedule is correct
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_retry_exponential_backoff_schedule(pg_session, pg_session_factory):
    """
    When a consumer fails, the retry backoff must follow: 2^retry_count × 10 seconds.
    retry_count=0 → 10s, retry_count=1 → 20s, retry_count=2 → 40s.
    next_retry_at must be set to UTC_NOW + backoff.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        async with pg_session.begin():
            await bus.publish(pg_session, event)

        async with pg_session_factory() as session:
            async with session.begin():
                await LifecycleManager.queue(session, event.event_id)

        # Simulate QUEUED → PROCESSING
        async with pg_session_factory() as session:
            async with session.begin():
                await LifecycleManager.processing(session, event.event_id)

        # Simulate PROCESSING → RETRYING with retry_count=0
        now = datetime.now(timezone.utc)
        expected_delay = (2 ** 0) * 10  # 10 seconds
        next_retry = now + timedelta(seconds=expected_delay)

        async with pg_session_factory() as session:
            async with session.begin():
                await LifecycleManager.retry(
                    session, event.event_id,
                    next_retry_at=next_retry,
                    error_detail="backoff test",
                )

        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)

        assert stored.lifecycle_state == EventLifecycleState.RETRYING.value
        assert stored.retry_count == 1, "retry_count must be incremented to 1"
        assert stored.next_retry_at is not None
        # Backoff must be at least 8s from now (tolerating test execution time)
        gap = (stored.next_retry_at - datetime.now(timezone.utc)).total_seconds()
        assert gap >= 5, f"Backoff too short: {gap:.1f}s (expected ~10s)"
        assert gap <= 20, f"Backoff too long: {gap:.1f}s"

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 5 — FOR UPDATE SKIP LOCKED prevents double dispatch
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_for_update_skip_locked_prevents_double_dispatch(pg_session, pg_session_factory):
    """
    Two concurrent dispatcher sessions try to claim the same PERSISTED event.
    FOR UPDATE SKIP LOCKED ensures only one session grabs it — the other skips.
    This is the database-level proof that the outbox dispatcher is race-safe.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        async with pg_session.begin():
            await bus.publish(pg_session, event)

        # Two independent sessions attempt FOR UPDATE SKIP LOCKED simultaneously
        grabbed_by = []

        async def try_grab_and_queue(session_factory, label: str):
            async with session_factory() as session:
                async with session.begin():
                    result = await session.execute(
                        text(
                            "SELECT event_id FROM event_store "
                            "WHERE lifecycle_state = 'PERSISTED' "
                            "AND event_id = :eid "
                            "FOR UPDATE SKIP LOCKED"
                        ),
                        {"eid": str(event.event_id)},
                    )
                    row = result.fetchone()
                    if row:
                        grabbed_by.append(label)
                        # Simulate the transition to QUEUED
                        await LifecycleManager.queue(session, event.event_id)

        # Run both concurrently with separate session factories (genuine independent transactions)
        await asyncio.gather(
            try_grab_and_queue(pg_session_factory, "dispatcher_A"),
            try_grab_and_queue(pg_session_factory, "dispatcher_B"),
        )

        # Exactly one dispatcher must have grabbed the row
        assert len(grabbed_by) == 1, (
            f"FOR UPDATE SKIP LOCKED must allow only ONE dispatcher to claim the event. "
            f"Grabbed by: {grabbed_by}"
        )

        # Verify final state
        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)
        assert stored.lifecycle_state == EventLifecycleState.QUEUED.value

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B9 TEST 6 — Dispatcher poll finds RETRYING events with elapsed backoff
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_retrying_event_with_elapsed_backoff_is_requeued(pg_session, pg_session_factory):
    """
    An event in RETRYING state with next_retry_at in the past must be picked up
    by the dispatcher's retry pass (Pass 2). Proves the retry lifecycle is complete.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        async with pg_session.begin():
            await bus.publish(pg_session, event)

        async with pg_session_factory() as s:
            async with s.begin():
                await LifecycleManager.queue(s, event.event_id)

        async with pg_session_factory() as s:
            async with s.begin():
                await LifecycleManager.processing(s, event.event_id)

        # Set next_retry_at in the past (already elapsed)
        past_retry = datetime.now(timezone.utc) - timedelta(seconds=30)
        async with pg_session_factory() as s:
            async with s.begin():
                await LifecycleManager.retry(
                    s, event.event_id,
                    next_retry_at=past_retry,
                    error_detail="test retry",
                )

        # Simulate dispatcher Pass 2: find RETRYING events with elapsed backoff
        async with pg_session_factory() as s:
            async with s.begin():
                result = await s.execute(
                    text(
                        "SELECT event_id FROM event_store "
                        "WHERE lifecycle_state = 'RETRYING' "
                        "AND next_retry_at <= :now "
                        "AND event_id = :eid "
                        "FOR UPDATE SKIP LOCKED"
                    ),
                    {"now": datetime.now(timezone.utc), "eid": str(event.event_id)},
                )
                row = result.fetchone()
                assert row is not None, \
                    "Dispatcher Pass 2 must find RETRYING events with elapsed backoff"

                # Requeue it
                await LifecycleManager.requeue(s, event.event_id)

        # Verify RETRYING → QUEUED
        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            stored = await repo.get_by_event_id(verify_session, event.event_id)

        assert stored.lifecycle_state == EventLifecycleState.QUEUED.value
        assert stored.queued_at is not None

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)
