"""
HunterOS Engage — Enterprise Idempotency Engine Test Suite
tests/events/test_idempotency_engine.py

Comprehensive tests covering:
1. Canonical payload hashing (key sorting, whitespace invariance, list order preservation, type normalization)
2. Deterministic idempotency key generation & collision resistance
3. Publish-time duplicate detection & webhook duplicate suppression
4. Concurrent publishing race condition & savepoint recovery
5. Retry execution key preservation
6. Replay execution duplicate bypass & audit history
7. Enriched duplicate audit logging
8. Idempotency metrics & lookup latency
9. Startup validation fail-fast guards
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import domain models to satisfy SQLAlchemy declarative base mapper configuration
from app.domain.conversations.models import Base
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory
from app.domain.dashboard.models import PipelineEvent
from app.domain.security.models import AuditLog
from app.domain.followup.models import (
    FollowUpQueue,
    FollowUpExecution,
    LeadHealthScore,
    SalesMemoryTimeline,
)
from app.domain.memory.models import CustomerMemory

from app.events.bus.event_bus import EventBus
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.idempotency.decision import (
    IdempotencyAction,
    IdempotencyConflictError,
    IdempotencyDecision,
)
from app.events.idempotency.engine import IdempotencyEngine
from app.events.idempotency.generator import IdempotencyKeyGenerator
from app.events.idempotency.hasher import CanonicalHasher
from app.events.idempotency.validator import (
    IdempotencyStartupValidationError,
    IdempotencyStartupValidator,
)
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.actor_types import ActorType
from app.events.model.categories import EventCategory
from app.events.model.lifecycle import EventLifecycleState
from app.events.observability.metrics import event_metrics
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_session():
    """Provides an isolated SQLite in-memory AsyncSession with EventRecord schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(EventRecord.__table__.create)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def reset_metrics():
    """Resets global event metrics before and after each test."""
    event_metrics.reset()
    yield
    event_metrics.reset()


# ── 1. Canonical Payload Hashing Tests ────────────────────────────────────────

def test_canonical_hashing_key_order_invariance():
    """Verify that dictionaries with different key orders produce identical hashes."""
    doc_1 = {"z": 100, "a": 1, "m": {"beta": "two", "alpha": "one"}}
    doc_2 = {"a": 1, "m": {"alpha": "one", "beta": "two"}, "z": 100}

    hash_1 = CanonicalHasher.hash_payload(doc_1)
    hash_2 = CanonicalHasher.hash_payload(doc_2)

    assert hash_1 == hash_2
    assert len(hash_1) == 64
    assert CanonicalHasher.to_canonical_json(doc_1) == '{"a":1,"m":{"alpha":"one","beta":"two"},"z":100}'


def test_canonical_hashing_whitespace_and_formatting():
    """Verify insignificant whitespace in raw representations produces canonical JSON."""
    raw_dict = {"title": "Deal Closed", "amount": 5000.0, "active": True, "notes": None}
    canonical = CanonicalHasher.to_canonical_json(raw_dict)

    assert canonical == '{"active":true,"amount":5000.0,"notes":null,"title":"Deal Closed"}'
    # Ensure no extraneous spaces around delimiters
    assert '": ' not in canonical
    assert ', ' not in canonical


def test_canonical_hashing_list_order_preserved():
    """Lists represent sequence-dependent domain data; different list order must yield different hashes."""
    doc_a = {"items": ["item1", "item2"]}
    doc_b = {"items": ["item2", "item1"]}

    hash_a = CanonicalHasher.hash_payload(doc_a)
    hash_b = CanonicalHasher.hash_payload(doc_b)

    assert hash_a != hash_b


def test_canonical_hashing_type_normalization():
    """Verify normalization of UUIDs, datetimes, booleans, and floats."""
    uid = UUID("12345678-1234-5678-1234-567812345678")
    dt_utc = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)

    normalized_uid = CanonicalHasher.normalize_value(uid)
    normalized_dt = CanonicalHasher.normalize_value(dt_utc)
    normalized_float = CanonicalHasher.normalize_value(0.0)

    assert normalized_uid == "12345678-1234-5678-1234-567812345678"
    assert normalized_dt == "2026-08-03T12:00:00+00:00"
    assert normalized_float == 0.0


def test_event_domain_payload_excludes_transient_fields():
    """Transient lifecycle fields (event_id, occurred_at, metadata) are excluded from domain payload hash."""
    w_id = uuid4()
    event_1 = CustomerRepliedEvent(
        workspace_id=w_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Interested in enterprise plan",
        wa_message_id="wa_msg_999",
    )
    # Simulate a duplicate event created slightly later with different event_id & occurred_at
    event_2 = CustomerRepliedEvent(
        workspace_id=w_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Interested in enterprise plan",
        wa_message_id="wa_msg_999",
    )

    assert event_1.event_id != event_2.event_id
    hash_1 = CanonicalHasher.hash_event_domain_payload(event_1)
    hash_2 = CanonicalHasher.hash_event_domain_payload(event_2)

    assert hash_1 == hash_2


# ── 2. Deterministic Key Generation & Collision Resistance Tests ─────────────

def test_idempotency_key_deterministic_and_collision_resistant():
    """Identical events generate identical keys; different events generate distinct keys."""
    generator = IdempotencyKeyGenerator()
    w_id = uuid4()
    corr_id = uuid4()

    event_a1 = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Pricing request",
        wa_message_id="msg_101",
    )
    event_a2 = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Pricing request",
        wa_message_id="msg_101",
    )
    # Different payload
    event_b = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Technical support request",
        wa_message_id="msg_102",
    )
    # Different workspace
    event_c = CustomerRepliedEvent(
        workspace_id=uuid4(),
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Pricing request",
        wa_message_id="msg_101",
    )

    key_a1 = generator.generate_key(event_a1)
    key_a2 = generator.generate_key(event_a2)
    key_b = generator.generate_key(event_b)
    key_c = generator.generate_key(event_c)

    assert key_a1 == key_a2
    assert len(key_a1) == 64
    assert key_a1 != key_b
    assert key_a1 != key_c
    assert key_b != key_c


def test_explicit_idempotency_key_preserved():
    """Explicit upstream idempotency key in event metadata or argument is respected."""
    generator = IdempotencyKeyGenerator()
    event = CustomerRepliedEvent(
        workspace_id=uuid4(),
        actor_type=ActorType.CUSTOMER,
        source_subsystem="webhook",
        message_content="Explicit key test",
        wa_message_id="msg_200",
        metadata={"idempotency_key": "custom-upstream-key-xyz-123"},
    )
    derived = generator.generate_key(event)
    assert derived == "custom-upstream-key-xyz-123"


# ── 3. Duplicate Webhook Delivery Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_webhook_delivery_suppression(async_session: AsyncSession):
    """
    Simulates receiving the same webhook 3 times:
    - 1st publish persists the event.
    - 2nd and 3rd publish detect duplicate, suppress persist, and return existing record without error.
    """
    repo = EventStoreRepository()
    engine = IdempotencyEngine(repo)
    service = EventStoreService(repo, idempotency_engine=engine)
    bus = EventBus(service)

    w_id = uuid4()
    corr_id = uuid4()

    # Incoming webhook 1
    event_1 = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="whatsapp_webhook",
        message_content="Please schedule demo for tomorrow at 3 PM",
        wa_message_id="wam_333444",
    )

    rec_1 = await bus.publish(async_session, event_1)
    await async_session.commit()

    assert rec_1 is not None
    assert rec_1.lifecycle_state == EventLifecycleState.PERSISTED.value
    assert rec_1.idempotency_key is not None
    assert rec_1.metadata_payload.get("idempotency_key") == rec_1.idempotency_key

    # Incoming webhook 2 (duplicate)
    event_2 = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="whatsapp_webhook",
        message_content="Please schedule demo for tomorrow at 3 PM",
        wa_message_id="wam_333444",
    )

    rec_2 = await bus.publish(async_session, event_2)
    assert rec_2 is not None
    assert rec_2.event_id == rec_1.event_id  # Returns the existing record

    # Incoming webhook 3 (duplicate)
    event_3 = CustomerRepliedEvent(
        workspace_id=w_id,
        correlation_id=corr_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="whatsapp_webhook",
        message_content="Please schedule demo for tomorrow at 3 PM",
        wa_message_id="wam_333444",
    )

    rec_3 = await bus.publish(async_session, event_3)
    assert rec_3 is not None
    assert rec_3.event_id == rec_1.event_id

    # Verify only 1 record exists in DB
    all_events = await repo.get_events(async_session, workspace_id=w_id)
    assert len(all_events) == 1

    # Verify metrics
    snap = event_metrics.snapshot()
    assert snap.duplicate_events_blocked == 2
    assert snap.idempotency_lookups == 3
    assert snap.duplicate_rate > 0.0


# ── 4. Concurrent Publishing & Savepoint Recovery Tests ────────────────────────

@pytest.mark.asyncio
async def test_concurrent_publish_race_recovery_via_savepoint(async_session: AsyncSession):
    """
    Simulates concurrent publishing race condition:
    Two publishers pass pre-lookup simultaneously, but the second encounters IntegrityError.
    Savepoint rollback rescues the transaction and retrieves the existing record cleanly.
    """
    repo = EventStoreRepository()
    engine = IdempotencyEngine(repo)
    service = EventStoreService(repo, idempotency_engine=engine)

    w_id = uuid4()
    event = CustomerRepliedEvent(
        workspace_id=w_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="race_test",
        message_content="Concurrent publish test",
        wa_message_id="wam_race_01",
    )

    # 1. First publish succeeds normally
    rec_1, dec_1 = await service.persist_event(async_session, event)
    assert dec_1.action == IdempotencyAction.PERSIST
    assert rec_1 is not None

    # 2. Simulate Worker 2 evaluated PERSIST concurrently (bypassing pre-lookup)
    # and directly calls repository.save_event with a duplicate record
    dup_record = EventRecord(
        event_id=uuid4(),
        schema_version=1,
        occurred_at=datetime.now(timezone.utc),
        workspace_id=w_id,
        actor_type="customer",
        source_subsystem="race_test",
        category="CONVERSATION",
        event_name="customer.replied",
        payload={"message_content": "Concurrent publish test"},
        metadata_payload={},
        idempotency_key=rec_1.idempotency_key,  # Same idempotency key!
        lifecycle_state=EventLifecycleState.PERSISTED.value,
        retry_count=0,
    )

    # Calling save_event raises IdempotencyConflictError from savepoint
    with pytest.raises(IdempotencyConflictError):
        await repo.save_event(async_session, dup_record)

    # Engine handles race conflict and recovers
    race_decision = await engine.handle_race_conflict(
        async_session,
        key=rec_1.idempotency_key,
        event=event,
    )

    assert race_decision.action == IdempotencyAction.RACE_RECOVERED
    assert race_decision.is_duplicate is True
    assert race_decision.existing_event.event_id == rec_1.event_id

    # Verify metrics for race recovery
    snap = event_metrics.snapshot()
    assert snap.uniqueness_conflicts == 1
    assert snap.duplicate_events_blocked == 1


# ── 5. Retry Compatibility Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_preserves_idempotency_key(async_session: AsyncSession):
    """
    Retries across the worker/dispatcher lifecycle must maintain the original
    idempotency_key without regenerating or modifying it.
    """
    repo = EventStoreRepository()
    engine = IdempotencyEngine(repo)
    service = EventStoreService(repo, idempotency_engine=engine)
    bus = EventBus(service)

    w_id = uuid4()
    event = CustomerRepliedEvent(
        workspace_id=w_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="retry_test",
        message_content="Retry key preservation",
        wa_message_id="msg_retry_1",
    )

    record = await bus.publish(async_session, event)
    original_key = record.idempotency_key
    await async_session.commit()

    # Transition PERSISTED -> QUEUED -> PROCESSING
    await LifecycleManager.queue(async_session, record.event_id)
    await LifecycleManager.processing(async_session, record.event_id)

    from datetime import timedelta

    # Fail and transition to RETRYING (Attempt 1)
    record = await LifecycleManager.retry(
        async_session,
        record.event_id,
        next_retry_at=datetime.now(timezone.utc) + timedelta(seconds=10),
        error_detail="Timeout connecting to external CRM",
    )
    await async_session.commit()

    assert record.lifecycle_state == EventLifecycleState.RETRYING.value
    assert record.retry_count == 1
    assert record.idempotency_key == original_key

    # Requeue and transition RETRYING -> QUEUED -> PROCESSING -> RETRYING (Attempt 2)
    record = await LifecycleManager.requeue(async_session, record.event_id)
    record = await LifecycleManager.processing(async_session, record.event_id)
    record = await LifecycleManager.retry(
        async_session,
        record.event_id,
        next_retry_at=datetime.now(timezone.utc) + timedelta(seconds=20),
        error_detail="CRM still unavailable",
    )
    await async_session.commit()

    assert record.retry_count == 2
    assert record.idempotency_key == original_key


# ── 6. Replay Compatibility Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_replay_duplicate_bypass(async_session: AsyncSession):
    """
    Replaying an event explicitly bypasses duplicate suppression,
    increments replay_bypasses, and produces IdempotencyAction.REPLAY_BYPASS.
    """
    repo = EventStoreRepository()
    engine = IdempotencyEngine(repo)
    service = EventStoreService(repo, idempotency_engine=engine)

    w_id = uuid4()
    event = CustomerRepliedEvent(
        workspace_id=w_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="replay_test",
        message_content="Replay test event",
        wa_message_id="msg_replay_1",
    )

    # 1. Initial publish
    rec_1, dec_1 = await service.persist_event(async_session, event)
    assert dec_1.action == IdempotencyAction.PERSIST

    # 2. Replay publish with is_replay=True
    dec_replay = await engine.evaluate(
        async_session,
        event=event,
        is_replay=True,
    )

    assert dec_replay.action == IdempotencyAction.REPLAY_BYPASS
    assert dec_replay.is_persisted is True
    assert dec_replay.is_duplicate is False

    snap = event_metrics.snapshot()
    assert snap.replay_bypasses == 1


# ── 7. Decision Model & Enriched Audit Logging Tests ──────────────────────────

def test_idempotency_decision_properties():
    """Verify properties and convenience helpers on IdempotencyDecision."""
    d_persist = IdempotencyDecision(action=IdempotencyAction.PERSIST, key="k1", reason="New")
    d_dup = IdempotencyDecision(action=IdempotencyAction.DUPLICATE, key="k2", reason="Exists")
    d_replay = IdempotencyDecision(action=IdempotencyAction.REPLAY_BYPASS, key="k3", reason="Replay")
    d_race = IdempotencyDecision(action=IdempotencyAction.RACE_RECOVERED, key="k4", reason="Race")

    assert d_persist.is_persisted is True
    assert d_persist.is_duplicate is False

    assert d_dup.is_persisted is False
    assert d_dup.is_duplicate is True

    assert d_replay.is_persisted is True
    assert d_replay.is_duplicate is False

    assert d_race.is_persisted is False
    assert d_race.is_duplicate is True


# ── 8. Metrics Snapshot & Lookup Latency Tests ─────────────────────────────────

def test_metrics_snapshot_and_latency_calculations():
    """Verify latency tracking and duplicate rate calculation in MetricsSnapshot."""
    event_metrics.increment("idempotency_keys_generated", 10)
    event_metrics.increment("duplicate_events_blocked", 2)
    event_metrics.record_idempotency_lookup(duration_ms=4.5)
    event_metrics.record_idempotency_lookup(duration_ms=5.5)

    snap = event_metrics.snapshot()
    assert snap.idempotency_keys_generated == 10
    assert snap.duplicate_events_blocked == 2
    assert snap.idempotency_lookups == 2
    assert snap.duplicate_rate == pytest.approx(2 / 12, 0.001)
    assert snap.avg_idempotency_lookup_latency_ms == pytest.approx(5.0, 0.1)

    d = snap.to_dict()
    assert "duplicate_rate" in d
    assert "avg_idempotency_lookup_latency_ms" in d


# ── 9. Startup Validation Fail-Fast Tests ──────────────────────────────────────

def test_startup_validator_success():
    """Startup validation succeeds against standard components."""
    IdempotencyStartupValidator.validate()


def test_startup_validator_fails_on_broken_hasher(monkeypatch):
    """Startup validation fails fast if canonical hashing is non-deterministic."""
    class BrokenHasher:
        _count = 0
        @classmethod
        def hash_payload(cls, data):
            cls._count += 1
            return f"hash_{cls._count}"

    with pytest.raises(IdempotencyStartupValidationError, match="Canonical hashing is non-deterministic"):
        IdempotencyStartupValidator.validate(hasher=BrokenHasher)
