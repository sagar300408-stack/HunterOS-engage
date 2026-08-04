"""
Scheduling Policy Framework for HunterOS Engage.

Provides extensible, pluggable scheduling strategies to prevent hot partition starvation
while preserving strict FIFO ordering within each individual partition.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set
from collections import deque

from app.events.store.models import EventRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractSchedulingPolicy(ABC):
    """
    Abstract interface for Partition Scheduling Policies.
    """

    @abstractmethod
    def schedule(
        self,
        partitioned_events: Dict[str, List[EventRecord]],
        batch_size: int,
        locked_partitions: Set[str],
        max_per_partition: int = 5,
    ) -> List[EventRecord]:
        """
        Plans the ordered list of EventRecords to schedule for execution.

        Args:
            partitioned_events: Map of partition_key -> List[EventRecord] (sorted by occurred_at ASC).
            batch_size: Maximum total events to include in the plan.
            locked_partitions: Set of partition_keys that are currently locked by active workers.
            max_per_partition: Maximum events to take from any single partition in this round.

        Returns:
            List of scheduled EventRecord instances.
        """
        pass


class RoundRobinSchedulingPolicy(AbstractSchedulingPolicy):
    """
    Round-Robin Partition Scheduling Policy.
    Iterates across active, non-locked partitions in round-robin order, taking events up to
    max_per_partition until batch_size is reached.
    Guarantees that a hot partition with 10,000 events cannot starve a partition with 10 events.
    """

    def schedule(
        self,
        partitioned_events: Dict[str, List[EventRecord]],
        batch_size: int,
        locked_partitions: Set[str],
        max_per_partition: int = 5,
    ) -> List[EventRecord]:
        scheduled: List[EventRecord] = []
        if not partitioned_events or batch_size <= 0:
            return scheduled

        # Filter out currently locked partitions and copy lists into deques
        active_queues: Dict[str, deque[EventRecord]] = {}
        partition_taken: Dict[str, int] = {}

        for p_key, events in partitioned_events.items():
            if p_key in locked_partitions:
                continue
            if events:
                active_queues[p_key] = deque(events)
                partition_taken[p_key] = 0

        if not active_queues:
            return scheduled

        # Round-robin cycle
        partition_keys = list(active_queues.keys())
        while len(scheduled) < batch_size and active_queues:
            exhausted_keys = []
            for p_key in partition_keys:
                if len(scheduled) >= batch_size:
                    break

                q = active_queues.get(p_key)
                if not q:
                    exhausted_keys.append(p_key)
                    continue

                if partition_taken[p_key] >= max_per_partition:
                    # Reached per-partition cap for this cycle
                    continue

                record = q.popleft()
                scheduled.append(record)
                partition_taken[p_key] += 1

                if not q or partition_taken[p_key] >= max_per_partition:
                    exhausted_keys.append(p_key)

            # Remove exhausted keys from next iteration
            for p_key in exhausted_keys:
                if p_key in active_queues and (not active_queues[p_key] or partition_taken[p_key] >= max_per_partition):
                    active_queues.pop(p_key, None)
            partition_keys = list(active_queues.keys())

        return scheduled


class DeficitRoundRobinSchedulingPolicy(AbstractSchedulingPolicy):
    """
    Deficit Round-Robin (DRR) Scheduling Policy.
    Uses per-partition deficit counters (quantum allocation) to balance throughput.
    """

    def __init__(self, quantum: int = 3):
        self.quantum = max(1, quantum)
        self._deficits: Dict[str, int] = {}

    def schedule(
        self,
        partitioned_events: Dict[str, List[EventRecord]],
        batch_size: int,
        locked_partitions: Set[str],
        max_per_partition: int = 5,
    ) -> List[EventRecord]:
        scheduled: List[EventRecord] = []
        if not partitioned_events or batch_size <= 0:
            return scheduled

        eligible_partitions = {
            k: deque(v) for k, v in partitioned_events.items()
            if k not in locked_partitions and v
        }

        if not eligible_partitions:
            return scheduled

        for p_key in list(eligible_partitions.keys()):
            if p_key not in self._deficits:
                self._deficits[p_key] = 0
            self._deficits[p_key] += self.quantum

        while len(scheduled) < batch_size and eligible_partitions:
            progress_made = False
            for p_key in list(eligible_partitions.keys()):
                if len(scheduled) >= batch_size:
                    break

                q = eligible_partitions[p_key]
                taken = 0

                while q and self._deficits[p_key] > 0 and len(scheduled) < batch_size and taken < max_per_partition:
                    record = q.popleft()
                    scheduled.append(record)
                    self._deficits[p_key] -= 1
                    taken += 1
                    progress_made = True

                if not q:
                    del eligible_partitions[p_key]
                    self._deficits[p_key] = 0

            if not progress_made:
                break

        return scheduled


class StrictFIFOSchedulingPolicy(AbstractSchedulingPolicy):
    """
    Strict FIFO scheduling across all partitions without fair quotas.
    Useful for benchmarks or strict chronological draining.
    """

    def schedule(
        self,
        partitioned_events: Dict[str, List[EventRecord]],
        batch_size: int,
        locked_partitions: Set[str],
        max_per_partition: int = 5,
    ) -> List[EventRecord]:
        all_eligible: List[EventRecord] = []
        for p_key, events in partitioned_events.items():
            if p_key in locked_partitions:
                continue
            all_eligible.extend(events)

        all_eligible.sort(key=lambda r: r.occurred_at)
        return all_eligible[:batch_size]


def get_scheduling_policy(policy_name: str) -> AbstractSchedulingPolicy:
    """
    Factory resolving policy instance from configured name.
    """
    norm = (policy_name or "").upper().strip()
    if norm == "DEFICIT_ROUND_ROBIN":
        return DeficitRoundRobinSchedulingPolicy()
    elif norm in ("FIFO", "STRICT_FIFO"):
        return StrictFIFOSchedulingPolicy()
    else:
        return RoundRobinSchedulingPolicy()
