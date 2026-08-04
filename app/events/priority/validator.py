"""
HunterOS Engage — Priority Startup Validator
app/events/priority/validator.py

Executes self-diagnostics on application startup to verify priority resolution,
scheduling deterministic invariants, virtual aging calculations, backpressure
flow control rules, and queue health monitoring.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.events.partitioning.ordering import OrderingPolicy
from app.events.priority.aging import PriorityAgingEngine
from app.events.priority.config import PriorityConfig
from app.events.priority.context import SchedulingContext
from app.events.priority.flow_control import FlowController, SystemLoadState
from app.events.priority.health import QueueHealthMonitor
from app.events.priority.priority import PriorityLevel, PriorityResolver
from app.events.priority.scheduler import DefaultPriorityScheduler
from app.events.store.models import EventRecord

logger = logging.getLogger(__name__)


class PriorityStartupValidationError(RuntimeError):
    """Raised when the priority subsystem fails boot diagnostics."""
    pass


class PriorityStartupValidator:
    """
    Startup diagnostic validator for the Priority & Flow Control Engine.
    """

    @classmethod
    def validate(cls) -> None:
        """
        Runs comprehensive self-checks. Raises PriorityStartupValidationError on failure.
        """
        logger.info("Initializing Priority & Flow Control Startup Validation...")
        try:
            config = PriorityConfig()

            # 1. Validate Priority Precedence Resolution
            cls._validate_priority_precedence()

            # 2. Validate Priority Aging Virtual Calculation
            cls._validate_priority_aging(config)

            # 3. Validate Intra-Partition FIFO Preservation & Inter-Partition Sorting
            cls._validate_priority_scheduler(config)

            # 4. Validate Flow Control & Non-Blocking Retry Guarantee
            cls._validate_flow_control(config)

            # 5. Validate Queue Health Monitor
            cls._validate_queue_health(config)

            logger.info("Priority & Flow Control Startup Validation PASSED.")

        except Exception as e:
            logger.error(f"Priority startup validation FAILED: {e}", exc_info=True)
            raise PriorityStartupValidationError(
                f"Priority subsystem failed startup diagnostic checks: {e}"
            ) from e

    @classmethod
    def _validate_priority_precedence(cls) -> None:
        # Category default: CONVERSATION -> HIGH
        rec_cat = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="CONVERSATION",
            event_name="customer.replied",
            actor_type="customer",
            source_subsystem="test",
            payload={},
            metadata_payload={},
        )
        assert PriorityResolver.resolve_priority(rec_cat) == PriorityLevel.HIGH, "Category priority resolution failed"

        # Explicit attribute override: LOW
        rec_cat.priority = 2
        assert PriorityResolver.resolve_priority(rec_cat) == PriorityLevel.LOW, "Attribute priority resolution failed"

        # Metadata override: CRITICAL
        rec_cat.metadata_payload = {"priority": "CRITICAL"}
        assert PriorityResolver.resolve_priority(rec_cat) == PriorityLevel.CRITICAL, "Metadata priority resolution failed"

    @classmethod
    def _validate_priority_aging(cls, config: PriorityConfig) -> None:
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(seconds=config.aging_threshold_seconds + config.aging_step_seconds + 5)
        rec = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="RESEARCH",
            event_name="research.completed",
            occurred_at=old_time,
            actor_type="system",
            source_subsystem="test",
            payload={},
            metadata_payload={},
        )
        base_prio = PriorityResolver.resolve_priority(rec)  # LOW (rank 2)
        eff_weight, is_aged = PriorityAgingEngine.calculate_effective_weight(
            record=rec,
            base_priority=base_prio,
            now=now,
            config=config,
        )
        assert is_aged is True, "Priority aging promotion failed"
        assert eff_weight > 2, "Effective weight not increased by aging"
        assert rec.priority == 0 or rec.priority is None, "Underlying record mutated during aging"

    @classmethod
    def _validate_priority_scheduler(cls, config: PriorityConfig) -> None:
        now = datetime.now(timezone.utc)
        conv_id = str(uuid4())

        # Partition 1 (Conversation): Two events. E1 occurred earlier with LOW, E2 occurred later with CRITICAL.
        # FIFO Invariant: E1 MUST be scheduled before E2 despite lower nominal priority.
        e1 = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="CONVERSATION",
            partition_key=f"conv:{conv_id}",
            occurred_at=now - timedelta(seconds=20),
            actor_type="customer",
            source_subsystem="test",
            payload={},
            metadata_payload={"priority": "LOW"},
        )
        e2 = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="CONVERSATION",
            partition_key=f"conv:{conv_id}",
            occurred_at=now - timedelta(seconds=10),
            actor_type="customer",
            source_subsystem="test",
            payload={},
            metadata_payload={"priority": "CRITICAL"},
        )

        scheduler = DefaultPriorityScheduler()
        ctx = SchedulingContext(
            candidate_records=[e2, e1],  # Passed out-of-order
            current_time=now,
            config=config,
        )
        plan = scheduler.plan(ctx)
        assert len(plan.scheduled_items) == 2
        assert plan.scheduled_items[0].event_id == e1.event_id, "Intra-partition FIFO order violated"
        assert plan.scheduled_items[1].event_id == e2.event_id, "Intra-partition FIFO order violated"

    @classmethod
    def _validate_flow_control(cls, config: PriorityConfig) -> None:
        controller = FlowController(config)
        scheduler = DefaultPriorityScheduler()
        now = datetime.now(timezone.utc)

        # Create 1 retry event and 1 low-priority event
        rec_retry = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="NOTIFICATION",
            occurred_at=now,
            lifecycle_state="RETRYING",
            actor_type="system",
            source_subsystem="test",
            payload={},
            metadata_payload={},
        )
        rec_low = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="AUDIT",
            occurred_at=now,
            lifecycle_state="PERSISTED",
            actor_type="system",
            source_subsystem="test",
            payload={},
            metadata_payload={},
        )

        ctx = SchedulingContext(
            candidate_records=[rec_low, rec_retry],
            current_time=now,
            config=config,
        )
        plan = scheduler.plan(ctx)

        # Under SATURATED health, low priority must be deferred, retry must be kept
        from app.events.priority.health import QueueHealthSnapshot
        sat_health = QueueHealthSnapshot(
            queue_depth=6000,
            dispatch_rate=100.0,
            completion_rate=100.0,
            retry_rate=0.0,
            dead_letter_rate=0.0,
            worker_utilization=1.0,
            oldest_pending_age_seconds=100.0,
            oldest_retry_age_seconds=10.0,
            partition_backlog=50,
            priority_distribution={},
            health_score=10.0,
            system_load_state="SATURATED",
            timestamp=now,
        )

        fc_plan = controller.apply_flow_control(plan, sat_health)
        scheduled_ids = [item.event_id for item in fc_plan.dispatches_to_execute]
        assert rec_retry.event_id in scheduled_ids, "Retry event was shed under saturated state"
        assert rec_low.event_id not in scheduled_ids, "Low priority event was not shed under saturated state"

    @classmethod
    def _validate_queue_health(cls, config: PriorityConfig) -> None:
        monitor = QueueHealthMonitor(config)
        now = datetime.now(timezone.utc)
        rec = EventRecord(
            event_id=uuid4(),
            workspace_id=uuid4(),
            category="CONVERSATION",
            occurred_at=now,
            actor_type="customer",
            source_subsystem="test",
            payload={},
            metadata_payload={},
        )
        snapshot = monitor.compute_snapshot([rec], now=now)
        assert snapshot.health_score > 80.0, "Healthy queue produced low health score"
        assert snapshot.system_load_state == "NORMAL", "Healthy queue produced abnormal load state"
