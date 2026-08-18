"""
B10 Certification — Event Idempotency
=====================================
Proves exactly-once semantics for event processing:
  1. Same event delivered once → one effect.
  2. Same event delivered twice sequentially → one effect.
  3. Same event delivered twice concurrently → one effect (real PostgreSQL locking).
  4. Workspace boundary isolation enforced in key.
  5. Idempotency key scoped correctly.
  6. Replay bypass bypasses idempotency constraints when `is_replay=True`.
"""

from __future__ import annotations

import asyncio
import uuid
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
from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.idempotency.engine import IdempotencyEngine
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService
from app.events.worker.tasks import _dispatch_async

from tests.domain.events.conftest import _delete_event_store_rows


def _make_bus() -> EventBus:
    return EventBus(store_service=EventStoreService(repository=EventStoreRepository()))


def _make_event(ws_id: uuid.UUID, *, wa_id: str | None = None) -> CustomerRepliedEvent:
    return CustomerRepliedEvent(
        workspace_id=ws_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="b10_test",
        message_content="B10 Idempotency test",
        wa_message_id=wa_id or f"wa_{uuid.uuid4().hex[:12]}",
    )


class CountableConsumer(EventConsumer):
    def __init__(self):
        self.call_count = 0

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [CustomerRepliedEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.call_count += 1


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 1 — Same event once → one effect
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_same_event_once_produces_one_effect(pg_session, pg_session_factory):
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)
    consumer = CountableConsumer()

    try:
        async with pg_session.begin():
            await bus.publish(pg_session, event)

        async with pg_session_factory() as session:
            async with session.begin():
                await LifecycleManager.queue(session, event.event_id)

        from app.events.registry import registry as global_registry
        original = global_registry._subscriptions.copy()
        global_registry._subscriptions.clear()
        global_registry.register(CustomerRepliedEvent, consumer)

        try:
            await _dispatch_async(event_id=event.event_id, max_retries=0)
        finally:
            global_registry._subscriptions.clear()
            global_registry._subscriptions.update(original)

        assert consumer.call_count == 1
    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 2 — Same event twice sequentially → one effect
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_same_event_twice_produces_one_effect(pg_session, pg_session_factory):
    """
    Publishing the exact same event instance twice sequentially must yield
    exactly one database record. The second publish request returns the
    pre-existing record via the idempotency fast-path.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        # First publish
        async with pg_session.begin():
            record1 = await bus.publish(pg_session, event)

        # Second publish in a new transaction
        async with pg_session_factory() as session2:
            async with session2.begin():
                record2 = await bus.publish(session2, event)

        assert record1.event_id == record2.event_id, "Second publish must return the original record"

        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            # We must only have 1 event for this workspace
            events = await repo.get_events(verify_session, workspace_id=ws_id)
            assert len(events) == 1, "There must be exactly one row in the DB"

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 3 — Concurrent duplicate delivery (REAL POSTGRESQL PARALLELISM)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_concurrent_duplicate_delivery_one_effect(pg_session_factory):
    """
    Two genuinely concurrent DB transactions attempt to publish the SAME event.
    One will win and insert. The other will hit the UNIQUE DB constraint,
    the SAVEPOINT will catch it, and it will return the winner's record.
    Result: Exactly ONE row in PostgreSQL.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)
    records_returned = []

    async def concurrent_publish():
        # Independent session/transaction for true concurrency
        async with pg_session_factory() as session:
            async with session.begin():
                record = await bus.publish(session, event)
                records_returned.append(record)

    try:
        # Run them in parallel using asyncio.gather
        await asyncio.gather(
            concurrent_publish(),
            concurrent_publish(),
        )

        assert len(records_returned) == 2
        # Both must point to the same underlying event_id in the DB
        assert records_returned[0].event_id == records_returned[1].event_id

        # Verify DB only has one row
        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            events = await repo.get_events(verify_session, workspace_id=ws_id)
            assert len(events) == 1

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 4 — Different events produce independent effects
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_different_events_produce_independent_effects(pg_session, pg_session_factory):
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event1 = _make_event(ws_id, wa_id="msg1")
    event2 = _make_event(ws_id, wa_id="msg2")  # Different payload

    try:
        async with pg_session.begin():
            record1 = await bus.publish(pg_session, event1)
            record2 = await bus.publish(pg_session, event2)

        assert record1.event_id != record2.event_id
        assert record1.idempotency_key != record2.idempotency_key

        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            events = await repo.get_events(verify_session, workspace_id=ws_id)
            assert len(events) == 2

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 5 — Workspace boundary preserved (Workspace A != Workspace B)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_workspace_boundary_preserved(pg_session, pg_session_factory):
    """
    Identical payloads from two different workspaces must result in distinct events.
    The idempotency key is scoped by workspace_id.
    """
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    bus = _make_bus()

    # Create two events that are identical EXCEPT for workspace_id
    event_a = CustomerRepliedEvent(
        workspace_id=ws_a,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="b10_test",
        message_content="Exact same content",
        wa_message_id="wa_same_123",
    )
    event_b = CustomerRepliedEvent(
        workspace_id=ws_b,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="b10_test",
        message_content="Exact same content",
        wa_message_id="wa_same_123",
    )

    try:
        async with pg_session.begin():
            record_a = await bus.publish(pg_session, event_a)
            record_b = await bus.publish(pg_session, event_b)

        assert record_a.event_id != record_b.event_id
        assert record_a.idempotency_key != record_b.idempotency_key

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_a)
        await _delete_event_store_rows(pg_session_factory, ws_b)


# ══════════════════════════════════════════════════════════════════════════════
# B10 TEST 6 — Replay bypass flag forces new event creation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b10_replay_bypass_reprocesses_without_duplication(pg_session, pg_session_factory):
    """
    When is_replay=True is passed, idempotency suppression is bypassed.
    A new EventRecord is created (new event_id, lifecycle_state=PERSISTED)
    so the consumer runs again without modifying the original historical record.
    """
    ws_id = uuid.uuid4()
    bus = _make_bus()
    event = _make_event(ws_id)

    try:
        # Original publish
        async with pg_session.begin():
            original_record = await bus.publish(pg_session, event)

        # Deliberate replay of the SAME event (semantically), but with a new event_id to satisfy PK constraint
        event2 = event.model_copy(update={"event_id": uuid.uuid4()})
        async with pg_session_factory() as session2:
            async with session2.begin():
                replay_record = await bus.publish(session2, event2, is_replay=True)

        # Must be two distinct database records
        assert replay_record.event_id != original_record.event_id
        # The replay record must not have the idempotency_key (or must have a salted one)
        # to avoid the UNIQUE constraint
        assert replay_record.idempotency_key != original_record.idempotency_key

        repo = EventStoreRepository()
        async with pg_session_factory() as verify_session:
            events = await repo.get_events(verify_session, workspace_id=ws_id)
            assert len(events) == 2

    finally:
        await _delete_event_store_rows(pg_session_factory, ws_id)
