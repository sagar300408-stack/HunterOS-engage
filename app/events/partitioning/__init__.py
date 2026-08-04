"""
HunterOS Engage - Enterprise Event Partitioning & Ordered Processing Subsystem.
"""

from app.events.partitioning.resolver import PartitionResolver
from app.events.partitioning.ordering import (
    OrderingPolicy,
    OrderingPolicyResolver,
    ORDERED_CATEGORIES,
    UNORDERED_CATEGORIES,
)
from app.events.partitioning.lock_manager import (
    AbstractPartitionLockManager,
    InMemoryPartitionLockManager,
    PartitionLockLease,
    get_lock_manager,
    set_lock_manager,
)
from app.events.partitioning.config import PartitionConfig, partition_config
from app.events.partitioning.fairness import (
    AbstractSchedulingPolicy,
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

__all__ = [
    "PartitionResolver",
    "OrderingPolicy",
    "OrderingPolicyResolver",
    "ORDERED_CATEGORIES",
    "UNORDERED_CATEGORIES",
    "AbstractPartitionLockManager",
    "InMemoryPartitionLockManager",
    "PartitionLockLease",
    "get_lock_manager",
    "set_lock_manager",
    "PartitionConfig",
    "partition_config",
    "AbstractSchedulingPolicy",
    "RoundRobinSchedulingPolicy",
    "DeficitRoundRobinSchedulingPolicy",
    "StrictFIFOSchedulingPolicy",
    "get_scheduling_policy",
    "EnterprisePartitionScheduler",
    "PartitionDispatchPlan",
    "ScheduledDispatch",
    "PartitionStartupValidator",
    "PartitionStartupValidationError",
]
