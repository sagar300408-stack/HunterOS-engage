"""
HunterOS Engage — Priority Engine & Flow Control Test Suite
tests/events/test_priority_engine.py

Comprehensive tests verifying:
  1. Priority level resolution and strict precedence hierarchy
  2. Non-mutating virtual priority aging and starvation prevention
  3. Strict FIFO preservation inside ORDERED partitions
  4. Inter-partition priority ranking and deterministic tie-breaking
  5. Pluggable AbstractPriorityScheduler interface polymorphism
  6. Queue health monitoring, health scores, and load state classification
  7. Adaptive backpressure, overload shedding, and non-blocking retry guarantees
  8. OutboxPoller end-to-end integration with SchedulingContext
  9. Reliability observability API endpoints (/priorities, /health/queue)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

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

from app.events.model.categories import EventCategory
from app.events.model.lifecycle import EventLifecycleState
from app.events.partitioning.ordering import OrderingPolicy
from app.events.partitioning.scheduler import EnterprisePartitionScheduler
from app.events.priority.aging import PriorityAgingEngine
from app.events.priority.config import PriorityConfig
from app.events.priority.context import (
    PriorityScheduledItem,
    PriorityScheduledPlan,
    SchedulingContext,
)
from app.events.priority.flow_control import (
    FlowController,
    FlowControlledDispatchPlan,
    SystemLoadState,
)
from app.events.priority.health import QueueHealthMonitor, QueueHealthSnapshot
from app.events.priority.priority import (
    PriorityLevel,
    PriorityResolver,
    PRIORITY_RANKS,
)
from app.events.priority.scheduler import (
    AbstractPriorityScheduler,
    DefaultPriorityScheduler,
)
from app.events.priority.validator import (
    PriorityStartupValidator,
    PriorityStartupValidationError,
)
from app.events.store.models import EventRecord
from app.events.dispatcher.poller import OutboxPoller
from app.events.observability.metrics import event_metrics


# ── 1. Priority Resolution & Precedence Tests ─────────────────────────────────

def test_priority_precedence_metadata_overrides_all():
    """Metadata priority must override both model attribute and category default."""
    now = datetime.now(timezone.utc)
    rec = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",  # Default HIGH
        event_name="customer.replied",
        priority=2,               # Attribute LOW
        metadata_payload={"priority": "CRITICAL"},  # Metadata CRITICAL
        occurred_at=now,
        actor_type="customer",
        source_subsystem="test",
        payload={},
    )
    prio = PriorityResolver.resolve_priority(rec)
    assert prio == PriorityLevel.CRITICAL


def test_priority_precedence_attribute_overrides_category():
    """Explicit priority rank attribute overrides category default."""
    now = datetime.now(timezone.utc)
    rec = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",  # Default HIGH (4)
        event_name="customer.replied",
        priority=1,               # Attribute BACKGROUND (1)
        metadata_payload={},
        occurred_at=now,
        actor_type="customer",
        source_subsystem="test",
        payload={},
    )
    prio = PriorityResolver.resolve_priority(rec)
    assert prio == PriorityLevel.BACKGROUND


def test_priority_category_defaults():
    """Category defaults are correctly resolved when no overrides exist."""
    now = datetime.now(timezone.utc)
    
    # CONVERSATION -> HIGH
    rec_conv = EventRecord(
        event_id=uuid4(), workspace_id=uuid4(), category="CONVERSATION",
        event_name="customer.replied", actor_type="customer", source_subsystem="test",
        payload={}, metadata_payload={}, occurred_at=now,
    )
    assert PriorityResolver.resolve_priority(rec_conv) == PriorityLevel.HIGH

    # CUSTOMER -> NORMAL
    rec_cust = EventRecord(
        event_id=uuid4(), workspace_id=uuid4(), category="CUSTOMER",
        event_name="customer.created", actor_type="system", source_subsystem="test",
        payload={}, metadata_payload={}, occurred_at=now,
    )
    assert PriorityResolver.resolve_priority(rec_cust) == PriorityLevel.NORMAL

    # RESEARCH -> LOW
    rec_res = EventRecord(
        event_id=uuid4(), workspace_id=uuid4(), category="RESEARCH",
        event_name="research.completed", actor_type="system", source_subsystem="test",
        payload={}, metadata_payload={}, occurred_at=now,
    )
    assert PriorityResolver.resolve_priority(rec_res) == PriorityLevel.LOW

    # AUDIT -> BACKGROUND
    rec_audit = EventRecord(
        event_id=uuid4(), workspace_id=uuid4(), category="AUDIT",
        event_name="audit.logged", actor_type="system", source_subsystem="test",
        payload={}, metadata_payload={}, occurred_at=now,
    )
    assert PriorityResolver.resolve_priority(rec_audit) == PriorityLevel.BACKGROUND


# ── 2. Virtual Priority Aging Tests ──────────────────────────────────────────

def test_priority_aging_boosts_virtual_weight_without_modifying_record():
    """Events waiting past the threshold get a virtual rank boost without DB mutation."""
    now = datetime.now(timezone.utc)
    config = PriorityConfig(
        enable_priority_aging=True,
        aging_threshold_seconds=60.0,
        aging_step_seconds=30.0,
        max_aging_boost=2,
    )

    # Event waited 130 seconds (exceeds 60s threshold by 70s -> 2 steps boost)
    old_time = now - timedelta(seconds=130)
    rec = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="AUDIT",  # Base rank 1 (BACKGROUND)
        event_name="audit.logged",
        occurred_at=old_time,
        priority=1,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={},
    )

    eff_weight, is_aged = PriorityAgingEngine.calculate_effective_weight(
        record=rec,
        base_priority=PriorityLevel.BACKGROUND,
        now=now,
        config=config,
    )

    assert is_aged is True
    assert eff_weight == 3  # 1 (base) + 2 (boost) = 3 (NORMAL)
    # Critical Invariant: Underlying stored record priority is NOT mutated
    assert rec.priority == 1


def test_priority_aging_disabled():
    """When aging is disabled, effective weight equals base rank."""
    now = datetime.now(timezone.utc)
    config = PriorityConfig(enable_priority_aging=False)
    old_time = now - timedelta(seconds=500)
    rec = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="AUDIT",
        event_name="audit.logged",
        occurred_at=old_time,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={},
    )

    eff_weight, is_aged = PriorityAgingEngine.calculate_effective_weight(
        record=rec,
        base_priority=PriorityLevel.BACKGROUND,
        now=now,
        config=config,
    )
    assert is_aged is False
    assert eff_weight == 1


# ── 3. Strict Intra-Partition FIFO Ordering Guarantee ────────────────────────

def test_intra_partition_fifo_order_preserved_despite_priority_differences():
    """
    CRITICAL INVARIANT:
    Inside the SAME partition, an event with an earlier occurred_at must ALWAYS
    be scheduled before a later event, even if the later event has higher priority.
    """
    now = datetime.now(timezone.utc)
    conv_id = str(uuid4())
    partition_key = f"conv:{conv_id}"

    # E1 occurred at T=0, nominal priority LOW (rank 2)
    e1 = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",
        partition_key=partition_key,
        occurred_at=now - timedelta(seconds=30),
        actor_type="customer",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "LOW"},
    )

    # E2 occurred at T=10, nominal priority CRITICAL (rank 5)
    e2 = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",
        partition_key=partition_key,
        occurred_at=now - timedelta(seconds=20),
        actor_type="customer",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "CRITICAL"},
    )

    scheduler = DefaultPriorityScheduler()
    # Pass them into context out of order (e2 before e1)
    ctx = SchedulingContext(
        candidate_records=[e2, e1],
        current_time=now,
        config=PriorityConfig(enable_priority_aging=False),
    )

    plan = scheduler.plan(ctx)
    assert len(plan.scheduled_items) == 2
    # E1 MUST BE FIRST
    assert plan.scheduled_items[0].event_id == e1.event_id
    assert plan.scheduled_items[1].event_id == e2.event_id


# ── 4. Inter-Partition Priority Ranking ───────────────────────────────────────

def test_inter_partition_priority_ordering():
    """
    Partitions with higher effective priority head events are scheduled ahead of lower ones.
    """
    now = datetime.now(timezone.utc)

    # Partition 1: Customer Conversation (HIGH)
    rec_high = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",
        partition_key="conv:high_1",
        occurred_at=now - timedelta(seconds=10),
        actor_type="customer",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "HIGH"},
    )

    # Partition 2: Urgent Conversation (CRITICAL)
    rec_crit = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",
        partition_key="conv:crit_1",
        occurred_at=now - timedelta(seconds=5),
        actor_type="customer",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "CRITICAL"},
    )

    # Partition 3: Audit Log (BACKGROUND)
    rec_low = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="AUDIT",
        partition_key="audit:low_1",
        occurred_at=now - timedelta(seconds=20),
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "BACKGROUND"},
    )

    scheduler = DefaultPriorityScheduler()
    ctx = SchedulingContext(
        candidate_records=[rec_low, rec_high, rec_crit],
        current_time=now,
        config=PriorityConfig(enable_priority_aging=False),
    )

    plan = scheduler.plan(ctx)
    scheduled_ids = [item.event_id for item in plan.scheduled_items]

    # CRITICAL partition first -> HIGH partition second -> BACKGROUND partition third
    assert scheduled_ids == [rec_crit.event_id, rec_high.event_id, rec_low.event_id]


# ── 5. Pluggable AbstractPriorityScheduler Polymorphism ──────────────────────

class ReversePriorityScheduler(AbstractPriorityScheduler):
    """Custom test scheduler reversing normal priority order."""
    def plan(self, context: SchedulingContext) -> PriorityScheduledPlan:
        items = []
        for r in context.candidate_records:
            items.append(
                PriorityScheduledItem(
                    event_id=r.event_id,
                    partition_key=r.partition_key or "default",
                    ordering_policy=OrderingPolicy.UNORDERED,
                    trace_id="trace_rev",
                    lock_timeout_seconds=30.0,
                    base_priority=PriorityLevel.LOW,
                    effective_weight=1,
                    is_aged=False,
                    record=r,
                )
            )
        items.reverse()
        return PriorityScheduledPlan(scheduled_items=items)


def test_abstract_priority_scheduler_extensibility():
    """Polymorphic scheduler implementation can be passed seamlessly via SchedulingContext."""
    r1 = EventRecord(event_id=uuid4(), category="CUSTOMER", actor_type="sys", source_subsystem="t", payload={}, metadata_payload={})
    r2 = EventRecord(event_id=uuid4(), category="CONVERSATION", actor_type="sys", source_subsystem="t", payload={}, metadata_payload={})

    custom_scheduler: AbstractPriorityScheduler = ReversePriorityScheduler()
    ctx = SchedulingContext(candidate_records=[r1, r2])
    plan = custom_scheduler.plan(ctx)

    assert plan.total_scheduled == 2
    assert plan.scheduled_items[0].event_id == r2.event_id
    assert plan.scheduled_items[1].event_id == r1.event_id


# ── 6. Queue Health Monitor & Load State Classification ──────────────────────

def test_queue_health_monitor_load_state_classification():
    """Evaluates queue depth and worker load to accurately compute load states."""
    monitor = QueueHealthMonitor(
        config=PriorityConfig(
            queue_depth_normal_threshold=10,
            queue_depth_busy_threshold=50,
            queue_depth_high_load_threshold=100,
            queue_depth_saturated_threshold=500,
        )
    )
    now = datetime.now(timezone.utc)

    # 5 events -> NORMAL
    records_normal = [
        EventRecord(
            event_id=uuid4(), category="CONVERSATION", occurred_at=now, actor_type="s",
            source_subsystem="t", payload={}, metadata_payload={},
        )
        for _ in range(5)
    ]
    snap_normal = monitor.compute_snapshot(records_normal, now=now)
    assert snap_normal.system_load_state == "NORMAL"
    assert snap_normal.health_score > 90.0

    # 150 events -> HIGH_LOAD
    records_high = [
        EventRecord(
            event_id=uuid4(), category="CONVERSATION", occurred_at=now, actor_type="s",
            source_subsystem="t", payload={}, metadata_payload={},
        )
        for _ in range(150)
    ]
    snap_high = monitor.compute_snapshot(records_high, now=now)
    assert snap_high.system_load_state == "HIGH_LOAD"

    # 600 events -> SATURATED
    records_sat = [
        EventRecord(
            event_id=uuid4(), category="CONVERSATION", occurred_at=now, actor_type="s",
            source_subsystem="t", payload={}, metadata_payload={},
        )
        for _ in range(600)
    ]
    snap_sat = monitor.compute_snapshot(records_sat, now=now)
    assert snap_sat.system_load_state == "SATURATED"
    assert snap_sat.health_score < 75.0


# ── 7. Adaptive Flow Controller & Non-Blocking Retry Invariant ────────────────

def test_flow_controller_saturated_emergency_shedding_and_retry_protection():
    """
    CRITICAL INVARIANTS:
    1. Under SATURATED load, NORMAL, LOW, and BACKGROUND events are deferred.
    2. RETRIES, REPLAYS, and CRITICAL events are NEVER shed or blocked.
    """
    now = datetime.now(timezone.utc)
    controller = FlowController(PriorityConfig(enable_backpressure=True))

    rec_retry = EventRecord(
        event_id=uuid4(),
        category="NOTIFICATION",
        lifecycle_state="RETRYING",
        occurred_at=now,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={},
    )
    rec_crit = EventRecord(
        event_id=uuid4(),
        category="CONVERSATION",
        occurred_at=now,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "CRITICAL"},
    )
    rec_norm = EventRecord(
        event_id=uuid4(),
        category="LEAD",
        occurred_at=now,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "NORMAL"},
    )
    rec_low = EventRecord(
        event_id=uuid4(),
        category="AUDIT",
        occurred_at=now,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "BACKGROUND"},
    )

    scheduler = DefaultPriorityScheduler()
    ctx = SchedulingContext(
        candidate_records=[rec_retry, rec_crit, rec_norm, rec_low],
        current_time=now,
        config=PriorityConfig(enable_priority_aging=False),
    )
    priority_plan = scheduler.plan(ctx)

    sat_health = QueueHealthSnapshot(
        queue_depth=1000,
        dispatch_rate=50.0,
        completion_rate=40.0,
        retry_rate=0.01,
        dead_letter_rate=0.0,
        worker_utilization=0.99,
        oldest_pending_age_seconds=120.0,
        oldest_retry_age_seconds=5.0,
        partition_backlog=50,
        priority_distribution={},
        health_score=20.0,
        system_load_state="SATURATED",
        timestamp=now,
    )

    flow_plan = controller.apply_flow_control(priority_plan, health=sat_health)

    executed_ids = [item.event_id for item in flow_plan.dispatches_to_execute]
    deferred_ids = [item.event_id for item in flow_plan.deferred_dispatches]

    # Invariant checks:
    assert rec_crit.event_id in executed_ids, "CRITICAL event was shed"
    assert rec_retry.event_id in executed_ids, "RETRY event was shed"
    assert rec_norm.event_id in deferred_ids, "NORMAL event was not shed under SATURATED"
    assert rec_low.event_id in deferred_ids, "BACKGROUND event was not shed under SATURATED"
    assert flow_plan.backpressure_active is True
    assert flow_plan.throttled_count == 2


# ── 8. Startup Validator Test ────────────────────────────────────────────────

def test_priority_startup_validator():
    """Startup diagnostic self-check runs and passes with default configurations."""
    PriorityStartupValidator.validate()


# ── 9. Outbox Poller Pipeline Integration Test ───────────────────────────────

@pytest.mark.asyncio
async def test_outbox_poller_orchestration_with_priority_and_health():
    """
    Verifies OutboxPoller orchestrating the full pipeline:
      Partition Scheduler -> Health Monitor -> Priority Scheduler -> Flow Controller -> Dispatch.
    """
    now = datetime.now(timezone.utc)
    e1 = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="CONVERSATION",
        partition_key="conv:outbox_1",
        occurred_at=now - timedelta(seconds=10),
        lifecycle_state=EventLifecycleState.PERSISTED.value,
        actor_type="customer",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "HIGH"},
    )
    e2 = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        category="AUDIT",
        partition_key="audit:outbox_2",
        occurred_at=now - timedelta(seconds=5),
        lifecycle_state=EventLifecycleState.PERSISTED.value,
        actor_type="system",
        source_subsystem="test",
        payload={},
        metadata_payload={"priority": "LOW"},
    )

    # Mock DB session & Celery App
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [e2, e1]
    mock_session.execute.return_value = mock_result
    mock_session.get.side_effect = lambda model, eid: e1 if eid == e1.event_id else e2
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    mock_celery = MagicMock()
    mock_celery.conf.broker_url = "memory://"

    poller = OutboxPoller(
        session_factory=mock_session_factory,
        celery_app=mock_celery,
        priority_config=PriorityConfig(enable_priority_aging=False),
    )

    await poller.poll_and_dispatch()

    # Verify celery task dispatches: e1 (HIGH) must be sent before e2 (LOW)
    assert mock_celery.send_task.call_count == 2
    call_args_list = mock_celery.send_task.call_args_list
    first_dispatched_id = call_args_list[0][1]["args"][0]
    second_dispatched_id = call_args_list[1][1]["args"][0]

    assert first_dispatched_id == str(e1.event_id)
    assert second_dispatched_id == str(e2.event_id)
    assert mock_session.commit.call_count == 1
