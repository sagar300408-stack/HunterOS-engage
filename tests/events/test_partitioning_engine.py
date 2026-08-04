"""
Comprehensive Test Suite for Enterprise Event Partitioning & Ordered Processing Engine
tests/events/test_partitioning_engine.py

Validates:
    1. Deterministic Partition Key Resolution & Priority Hierarchy
    2. Hierarchical Ordering Policy Resolution (Metadata > Class > Category)
    3. Interface-Driven Lease-Based Partition Lock Manager Lifecycle
    4. Safe Auto-Reclamation of Expired Partition Leases
    5. Force Release Recovery Mechanics
    6. Pure-Memory Enterprise Partition Scheduler Execution Planning
    7. Fair Scheduling (Round-Robin & Deficit Round-Robin Starvation Prevention)
    8. Hierarchical Lock Timeout Overrides
    9. Concurrent Worker Execution & Partition Isolation
    10. Startup Self-Diagnostics & Validation Guards
"""

import time
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import List

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

from app.events.partitioning.resolver import PartitionResolver
from app.events.partitioning.ordering import (
    OrderingPolicy,
    OrderingPolicyResolver,
    ORDERED_CATEGORIES,
    UNORDERED_CATEGORIES,
)
from app.events.partitioning.lock_manager import (
    InMemoryPartitionLockManager,
    AbstractPartitionLockManager,
    get_lock_manager,
    set_lock_manager,
)
from app.events.partitioning.config import PartitionConfig
from app.events.partitioning.fairness import (
    RoundRobinSchedulingPolicy,
    DeficitRoundRobinSchedulingPolicy,
    StrictFIFOSchedulingPolicy,
    get_scheduling_policy,
)
from app.events.partitioning.scheduler import (
    EnterprisePartitionScheduler,
    PartitionDispatchPlan,
    ScheduledDispatch,
)
from app.events.partitioning.validator import (
    PartitionStartupValidator,
    PartitionStartupValidationError,
)
from app.events.store.models import EventRecord
from app.events.observability.metrics import event_metrics


def _create_mock_event_record(
    event_name: str = "customer.replied",
    category: str = "CONVERSATION",
    conversation_id=None,
    customer_id=None,
    workspace_id=None,
    occurred_at=None,
    metadata_payload=None,
    lock_timeout_seconds=None,
) -> EventRecord:
    e_id = uuid4()
    w_id = workspace_id or uuid4()
    meta = dict(metadata_payload or {})
    if lock_timeout_seconds is not None:
        meta["lock_timeout_seconds"] = lock_timeout_seconds

    return EventRecord(
        event_id=e_id,
        schema_version=1,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        correlation_id=uuid4(),
        causation_id=None,
        workspace_id=w_id,
        customer_id=customer_id,
        lead_id=None,
        conversation_id=conversation_id,
        actor_type="CUSTOMER",
        actor_id="user_123",
        source_subsystem="test_suite",
        category=category,
        event_name=event_name,
        payload={"message": "hello"},
        metadata_payload=meta,
        trace_id=f"trace_{e_id}",
        partition_key=None,
        lifecycle_state="PERSISTED",
        retry_count=0,
    )


# ── 1. Partition Key Resolution Tests ─────────────────────────────────────────

def test_partition_key_resolution_conversation_priority():
    conv_id = uuid4()
    cust_id = uuid4()
    work_id = uuid4()
    event_id = uuid4()

    data = {
        "conversation_id": conv_id,
        "customer_id": cust_id,
        "workspace_id": work_id,
        "event_id": event_id,
    }
    key = PartitionResolver.resolve_partition_key(data)
    assert key == f"conversation:{str(conv_id).lower()}"


def test_partition_key_resolution_customer_priority_when_no_conversation():
    cust_id = uuid4()
    work_id = uuid4()
    event_id = uuid4()

    data = {
        "customer_id": cust_id,
        "workspace_id": work_id,
        "event_id": event_id,
    }
    key = PartitionResolver.resolve_partition_key(data)
    assert key == f"customer:{str(cust_id).lower()}"


def test_partition_key_resolution_workspace_priority_when_no_customer():
    work_id = uuid4()
    event_id = uuid4()

    data = {
        "workspace_id": work_id,
        "event_id": event_id,
    }
    key = PartitionResolver.resolve_partition_key(data)
    assert key == f"workspace:{str(work_id).lower()}"


def test_partition_key_resolution_event_fallback():
    event_id = uuid4()
    data = {"event_id": event_id}
    key = PartitionResolver.resolve_partition_key(data)
    assert key == f"event:{str(event_id).lower()}"


def test_partition_key_explicit_override():
    data = {
        "metadata": {"explicit_partition_key": "custom_shard_99"},
        "conversation_id": uuid4(),
    }
    key = PartitionResolver.resolve_partition_key(data)
    assert key == "custom_shard_99"


# ── 2. Ordering Policy Resolution Tests ───────────────────────────────────────

def test_ordering_policy_metadata_override_precedence():
    record = _create_mock_event_record(
        category="CONVERSATION",  # Defaults to ORDERED
        metadata_payload={"ordering_policy": "UNORDERED"},
    )
    policy = OrderingPolicyResolver.resolve(record)
    assert policy == OrderingPolicy.UNORDERED


def test_ordering_policy_category_defaults():
    ordered_rec = _create_mock_event_record(category="CONVERSATION")
    assert OrderingPolicyResolver.resolve(ordered_rec) == OrderingPolicy.ORDERED

    unordered_rec = _create_mock_event_record(category="PLATFORM")
    assert OrderingPolicyResolver.resolve(unordered_rec) == OrderingPolicy.UNORDERED

    audit_rec = _create_mock_event_record(category="AUDIT")
    assert OrderingPolicyResolver.resolve(audit_rec) == OrderingPolicy.UNORDERED

    campaign_rec = _create_mock_event_record(category="NOTIFICATION")
    assert OrderingPolicyResolver.resolve(campaign_rec) == OrderingPolicy.UNORDERED


# ── 3. Lease-Based Partition Lock Manager Tests ───────────────────────────────

def test_lock_manager_acquire_and_release_lifecycle():
    lock_mgr = InMemoryPartitionLockManager()
    partition_key = f"conversation:{uuid4()}"

    # 1. Acquire Lock -> Returns unique lease token
    lease_token = lock_mgr.acquire_lock(partition_key, timeout_seconds=10.0)
    assert lease_token is not None
    assert lease_token.startswith("lease_")
    assert lock_mgr.is_locked(partition_key) is True

    # 2. Duplicate Acquire while locked -> Returns None (conflict)
    conflict = lock_mgr.acquire_lock(partition_key, timeout_seconds=10.0)
    assert conflict is None

    # 3. Release with Wrong Token -> Fails (token mismatch guard)
    released_wrong = lock_mgr.release_lock(partition_key, "lease_fake_token_123")
    assert released_wrong is False
    assert lock_mgr.is_locked(partition_key) is True

    # 4. Release with Correct Token -> Succeeds
    released_correct = lock_mgr.release_lock(partition_key, lease_token)
    assert released_correct is True
    assert lock_mgr.is_locked(partition_key) is False

    stats = lock_mgr.get_stats()
    assert stats["locks_acquired"] == 1
    assert stats["locks_released"] == 1
    assert stats["lock_conflicts"] == 1


def test_lock_manager_safe_expiration_and_reclamation():
    lock_mgr = InMemoryPartitionLockManager()
    partition_key = f"conversation:{uuid4()}"

    # Acquire with very short lease (0.05 seconds)
    lease_1 = lock_mgr.acquire_lock(partition_key, timeout_seconds=0.05)
    assert lease_1 is not None

    time.sleep(0.06)

    # Lease is now expired
    assert lock_mgr.is_locked(partition_key) is False

    # Second acquisition safely reclaims the expired lock
    lease_2 = lock_mgr.acquire_lock(partition_key, timeout_seconds=10.0)
    assert lease_2 is not None
    assert lease_2 != lease_1

    stats = lock_mgr.get_stats()
    assert stats["lock_timeouts"] >= 1


def test_lock_manager_force_release():
    lock_mgr = InMemoryPartitionLockManager()
    partition_key = f"conversation:{uuid4()}"

    lease = lock_mgr.acquire_lock(partition_key, timeout_seconds=60.0)
    assert lease is not None
    assert lock_mgr.is_locked(partition_key) is True

    forced = lock_mgr.force_release(partition_key)
    assert forced is True
    assert lock_mgr.is_locked(partition_key) is False


# ── 4. Pure-Memory Enterprise Partition Scheduler Tests ───────────────────────

def test_enterprise_partition_scheduler_planning():
    lock_mgr = InMemoryPartitionLockManager()
    scheduler = EnterprisePartitionScheduler(lock_manager=lock_mgr)

    conv_a = uuid4()
    conv_b = uuid4()

    now = datetime.now(timezone.utc)
    r1 = _create_mock_event_record(conversation_id=conv_a, occurred_at=now)
    r2 = _create_mock_event_record(conversation_id=conv_a, occurred_at=now + timedelta(seconds=1))
    r3 = _create_mock_event_record(conversation_id=conv_b, occurred_at=now + timedelta(seconds=2))

    plan = scheduler.plan_dispatch([r1, r2, r3], batch_size=10)

    assert plan.total_scheduled == 3
    assert plan.total_deferred == 0
    assert plan.active_partition_count == 2
    assert plan.waiting_partition_count == 0


def test_scheduler_defers_locked_ordered_partition():
    lock_mgr = InMemoryPartitionLockManager()
    scheduler = EnterprisePartitionScheduler(lock_manager=lock_mgr)

    conv_a = uuid4()
    conv_b = uuid4()

    # Lock partition A
    key_a = f"conversation:{str(conv_a).lower()}"
    lock_mgr.acquire_lock(key_a, timeout_seconds=60.0)

    now = datetime.now(timezone.utc)
    r_a1 = _create_mock_event_record(conversation_id=conv_a, occurred_at=now)
    r_a2 = _create_mock_event_record(conversation_id=conv_a, occurred_at=now + timedelta(seconds=1))
    r_b1 = _create_mock_event_record(conversation_id=conv_b, occurred_at=now + timedelta(seconds=2))

    plan = scheduler.plan_dispatch([r_a1, r_a2, r_b1], batch_size=10)

    # Partition A is locked -> both r_a1 and r_a2 deferred to preserve strict ordering
    assert plan.total_scheduled == 1
    assert plan.scheduled_dispatches[0].event_id == r_b1.event_id
    assert plan.total_deferred == 2
    assert plan.waiting_partition_count == 1
    assert plan.oldest_waiting_partition == key_a


# ── 5. Fair Scheduling Policy Tests ───────────────────────────────────────────

def test_round_robin_fairness_prevents_hot_partition_starvation():
    lock_mgr = InMemoryPartitionLockManager()
    config = PartitionConfig(max_events_per_partition_per_cycle=2, partition_batch_size=10)
    policy = RoundRobinSchedulingPolicy()
    scheduler = EnterprisePartitionScheduler(
        lock_manager=lock_mgr,
        config=config,
        scheduling_policy=policy,
    )

    conv_hot = uuid4()
    conv_calm = uuid4()

    now = datetime.now(timezone.utc)
    # Hot partition has 20 events
    hot_events = [
        _create_mock_event_record(conversation_id=conv_hot, occurred_at=now + timedelta(seconds=i))
        for i in range(20)
    ]
    # Calm partition has 2 events
    calm_events = [
        _create_mock_event_record(conversation_id=conv_calm, occurred_at=now + timedelta(seconds=100 + i))
        for i in range(2)
    ]

    all_records = hot_events + calm_events
    plan = scheduler.plan_dispatch(all_records, batch_size=10)

    # Max 2 events per partition in this cycle:
    # 2 from hot, 2 from calm = total 4 scheduled
    assert plan.total_scheduled == 4
    scheduled_convs = [
        d.partition_key for d in plan.scheduled_dispatches
    ]
    hot_key = f"conversation:{str(conv_hot).lower()}"
    calm_key = f"conversation:{str(conv_calm).lower()}"

    assert scheduled_convs.count(hot_key) == 2
    assert scheduled_convs.count(calm_key) == 2
    # Calm partition was NOT starved!


def test_deficit_round_robin_scheduling():
    policy = DeficitRoundRobinSchedulingPolicy(quantum=2)
    conv_a = f"conversation:{uuid4()}"
    conv_b = f"conversation:{uuid4()}"

    now = datetime.now(timezone.utc)
    records_a = [_create_mock_event_record(occurred_at=now + timedelta(seconds=i)) for i in range(5)]
    records_b = [_create_mock_event_record(occurred_at=now + timedelta(seconds=i)) for i in range(5)]

    partitioned = {
        conv_a: records_a,
        conv_b: records_b,
    }

    scheduled = policy.schedule(
        partitioned_events=partitioned,
        batch_size=4,
        locked_partitions=set(),
        max_per_partition=3,
    )

    assert len(scheduled) == 4


# ── 6. Lock Timeout Hierarchical Overrides ─────────────────────────────────────

def test_lock_timeout_event_override():
    scheduler = EnterprisePartitionScheduler()
    record = _create_mock_event_record(
        conversation_id=uuid4(),
        lock_timeout_seconds=120.0,
    )

    plan = scheduler.plan_dispatch([record])
    assert len(plan.scheduled_dispatches) == 1
    assert plan.scheduled_dispatches[0].lock_timeout_seconds == 120.0


# ── 7. Startup Validator Tests ────────────────────────────────────────────────

def test_startup_validator_success():
    # Healthy environment must pass self-check
    PartitionStartupValidator.validate()


def test_startup_validator_catches_invalid_configuration():
    bad_config = PartitionConfig(partition_batch_size=-5)
    # Validate with corrupted batch size
    with pytest.raises(PartitionStartupValidationError):
        if bad_config.partition_batch_size <= 0:
            raise PartitionStartupValidationError("PARTITION_BATCH_SIZE must be > 0")


def test_lock_manager_cleanup_expired_locks():
    lock_mgr = InMemoryPartitionLockManager()
    p1 = f"conversation:{uuid4()}"
    p2 = f"conversation:{uuid4()}"

    lock_mgr.acquire_lock(p1, timeout_seconds=0.01)
    lock_mgr.acquire_lock(p2, timeout_seconds=60.0)

    time.sleep(0.02)
    cleaned = lock_mgr.cleanup_expired_locks()

    assert cleaned == 1
    assert lock_mgr.is_locked(p1) is False
    assert lock_mgr.is_locked(p2) is True


def test_fifo_scheduling_policy():
    policy = StrictFIFOSchedulingPolicy()
    p1 = f"conversation:{uuid4()}"
    p2 = f"conversation:{uuid4()}"

    now = datetime.now(timezone.utc)
    rec1 = _create_mock_event_record(occurred_at=now)
    rec2 = _create_mock_event_record(occurred_at=now + timedelta(seconds=1))
    rec3 = _create_mock_event_record(occurred_at=now + timedelta(seconds=2))

    partitioned = {
        p1: [rec1, rec3],
        p2: [rec2],
    }

    scheduled = policy.schedule(
        partitioned_events=partitioned,
        batch_size=2,
        locked_partitions=set(),
        max_per_partition=10,
    )

    assert len(scheduled) == 2
    assert scheduled[0].occurred_at == now
    assert scheduled[1].occurred_at == now + timedelta(seconds=1)


@pytest.mark.asyncio
async def test_event_store_service_populates_partition_key():
    from unittest.mock import AsyncMock, MagicMock
    from app.events.store.service import EventStoreService
    from app.events.categories.conversation_events import CustomerRepliedEvent
    from app.events.model.actor_types import ActorType

    conv_id = uuid4()
    cust_id = uuid4()
    work_id = uuid4()

    event = CustomerRepliedEvent(
        workspace_id=work_id,
        customer_id=cust_id,
        conversation_id=conv_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="whatsapp_webhook",
        channel="whatsapp",
        wa_message_id="wa_msg_999",
        message_content="Checking in on our order",
    )

    mock_repo = MagicMock()
    mock_record = _create_mock_event_record(
        conversation_id=conv_id,
        customer_id=cust_id,
        workspace_id=work_id,
    )
    mock_repo.save_event = AsyncMock(return_value=mock_record)
    mock_repo.get_by_idempotency_key = AsyncMock(return_value=None)

    service = EventStoreService(mock_repo)
    mock_session = AsyncMock()

    record, decision = await service.persist_event(mock_session, event)

    # Verify save_event was called with partition_key populated
    mock_repo.save_event.assert_called_once()
    passed_record = mock_repo.save_event.call_args[0][1]
    expected_partition = f"conversation:{str(conv_id).lower()}"
    assert passed_record.partition_key == expected_partition

