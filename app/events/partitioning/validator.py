"""
Startup Validator for Event Partitioning Subsystem in HunterOS Engage.

Ensures fail-fast startup checks for:
    - Partition resolution engine determinism.
    - Ordering policy resolution precedence.
    - Partition lock manager interface and lease lifecycle.
    - Scheduler execution planning contract.
    - Partition configuration validity.
"""

from uuid import uuid4
from datetime import datetime, timezone

from app.events.partitioning.resolver import PartitionResolver
from app.events.partitioning.ordering import OrderingPolicy, OrderingPolicyResolver
from app.events.partitioning.lock_manager import (
    AbstractPartitionLockManager,
    get_lock_manager,
)
from app.events.partitioning.config import partition_config
from app.events.partitioning.scheduler import EnterprisePartitionScheduler
from app.events.store.models import EventRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PartitionStartupValidationError(RuntimeError):
    """Raised when partitioning subsystem validation fails during application startup."""
    pass


class PartitionStartupValidator:
    """
    Validates the partitioning and ordering infrastructure at application startup.
    """

    @classmethod
    def validate(cls) -> None:
        """
        Runs comprehensive self-diagnostics on the partitioning subsystem.

        Raises:
            PartitionStartupValidationError: If any critical validation check fails.
        """
        logger.info("partition_startup_validation_starting")

        try:
            # 1. Validate Configuration
            if partition_config.partition_batch_size <= 0:
                raise PartitionStartupValidationError("PARTITION_BATCH_SIZE must be > 0")
            if partition_config.max_active_partitions <= 0:
                raise PartitionStartupValidationError("MAX_ACTIVE_PARTITIONS must be > 0")
            if partition_config.lock_timeout_seconds <= 0:
                raise PartitionStartupValidationError("PARTITION_LOCK_TIMEOUT_SECONDS must be > 0")

            # 2. Validate PartitionResolver Determinism
            test_conv_id = uuid4()
            test_cust_id = uuid4()
            test_work_id = uuid4()
            test_event_id = uuid4()

            key_conv = PartitionResolver.resolve_partition_key({
                "conversation_id": test_conv_id,
                "customer_id": test_cust_id,
                "workspace_id": test_work_id,
                "event_id": test_event_id,
            })
            if key_conv != f"conversation:{str(test_conv_id).lower()}":
                raise PartitionStartupValidationError(
                    f"PartitionResolver priority mismatch: expected conversation prefix, got '{key_conv}'"
                )

            key_cust = PartitionResolver.resolve_partition_key({
                "customer_id": test_cust_id,
                "workspace_id": test_work_id,
                "event_id": test_event_id,
            })
            if key_cust != f"customer:{str(test_cust_id).lower()}":
                raise PartitionStartupValidationError(
                    f"PartitionResolver customer priority mismatch, got '{key_cust}'"
                )

            # 3. Validate OrderingPolicyResolver Precedence
            # Metadata override
            policy_meta = OrderingPolicyResolver.resolve({
                "category": "CONVERSATION",
                "metadata": {"ordering_policy": "UNORDERED"},
            })
            if policy_meta != OrderingPolicy.UNORDERED:
                raise PartitionStartupValidationError(
                    f"OrderingPolicyResolver failed metadata override precedence: got {policy_meta}"
                )

            # Category default
            policy_cat = OrderingPolicyResolver.resolve({
                "category": "CONVERSATION",
                "metadata": {},
            })
            if policy_cat != OrderingPolicy.ORDERED:
                raise PartitionStartupValidationError(
                    f"OrderingPolicyResolver failed category default for CONVERSATION: got {policy_cat}"
                )

            # 4. Validate Lock Manager Interface & Lease Lifecycle
            lock_mgr = get_lock_manager()
            if not isinstance(lock_mgr, AbstractPartitionLockManager):
                raise PartitionStartupValidationError(
                    f"Lock manager does not implement AbstractPartitionLockManager: {type(lock_mgr)}"
                )

            test_partition = f"test:startup:{uuid4().hex}"
            lease = lock_mgr.acquire_lock(test_partition, timeout_seconds=5.0)
            if not lease:
                raise PartitionStartupValidationError("Lock manager failed to acquire test lock lease")

            # Duplicate acquisition while locked must fail
            conflict = lock_mgr.acquire_lock(test_partition, timeout_seconds=5.0)
            if conflict is not None:
                raise PartitionStartupValidationError("Lock manager allowed conflicting concurrent lease acquisition")

            # Release with correct token must succeed
            released = lock_mgr.release_lock(test_partition, lease)
            if not released:
                raise PartitionStartupValidationError("Lock manager failed to release lease with valid token")

            # 5. Validate Scheduler Pure Planning Contract
            scheduler = EnterprisePartitionScheduler(lock_manager=lock_mgr)
            dummy_record = EventRecord(
                event_id=uuid4(),
                workspace_id=test_work_id,
                conversation_id=test_conv_id,
                actor_type="SYSTEM",
                source_subsystem="startup_validation",
                category="CONVERSATION",
                event_name="test.event",
                occurred_at=datetime.now(timezone.utc),
                payload={"msg": "startup_test"},
                metadata_payload={},
            )
            plan = scheduler.plan_dispatch([dummy_record], batch_size=10)
            if len(plan.scheduled_dispatches) != 1:
                raise PartitionStartupValidationError(
                    f"Scheduler failed to plan dispatch: expected 1 scheduled, got {len(plan.scheduled_dispatches)}"
                )

            logger.info("partition_startup_validation_passed")

        except Exception as e:
            logger.critical("partition_startup_validation_failed", error=str(e), exc_info=True)
            if isinstance(e, PartitionStartupValidationError):
                raise
            raise PartitionStartupValidationError(f"Partition startup self-check failed: {e}") from e
