"""
HunterOS Engage — Interface-Driven Priority Scheduling Engine
app/events/priority/scheduler.py

Defines AbstractPriorityScheduler and DefaultPriorityScheduler.
Performs pure in-memory scheduling planning that respects strict per-partition FIFO
ordering while prioritizing higher-priority streams and applying virtual aging.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional

from app.events.partitioning.ordering import OrderingPolicy, OrderingPolicyResolver
from app.events.partitioning.resolver import PartitionResolver
from app.events.priority.aging import PriorityAgingEngine
from app.events.priority.context import (
    PriorityScheduledItem,
    PriorityScheduledPlan,
    SchedulingContext,
)
from app.events.priority.priority import (
    PriorityLevel,
    PriorityResolver,
    RANK_TO_PRIORITY,
)
from app.events.store.models import EventRecord

logger = logging.getLogger(__name__)


class AbstractPriorityScheduler(ABC):
    """
    Abstract interface for all priority scheduling strategies.
    Enables pluggable scheduling algorithms (Default, EDF, Weighted Fair, SLA-aware).
    """

    @abstractmethod
    def plan(self, context: SchedulingContext) -> PriorityScheduledPlan:
        """
        Pure-planning execution: takes an immutable SchedulingContext and returns
        a deterministically ordered PriorityScheduledPlan.
        """
        raise NotImplementedError


class DefaultPriorityScheduler(AbstractPriorityScheduler):
    """
    Production default priority scheduler.

    Invariants:
    1. Preserves strict FIFO chronological order (occurred_at ASC) inside each partition.
    2. Sorts partitions by the effective weight of their head (earliest) event.
    3. Sorts unordered events by effective weight DESC, then occurred_at ASC, then event_id ASC.
    4. Deterministic tie-breaking using partition_key and event_id across all poller instances.
    """

    def plan(self, context: SchedulingContext) -> PriorityScheduledPlan:
        # Determine items to schedule
        # If PartitionDispatchPlan is present, use its scheduled items; otherwise resolve from candidate_records
        items_to_process: List[EventRecord] = []
        if context.partition_plan and context.partition_plan.scheduled_dispatches:
            # Map scheduled partition items to their original EventRecord
            record_map = {r.event_id: r for r in context.candidate_records}
            for d in context.partition_plan.scheduled_dispatches:
                rec = record_map.get(d.event_id)
                if rec:
                    items_to_process.append(rec)
        else:
            items_to_process = list(context.candidate_records)

        if not items_to_process:
            return PriorityScheduledPlan()

        # Group events by partition
        partition_groups: Dict[str, List[EventRecord]] = defaultdict(list)
        for record in items_to_process:
            pkey = record.partition_key or PartitionResolver.resolve_partition_key(record)
            partition_groups[pkey].append(record)

        # Sort intra-partition records strictly by occurred_at ASC, then event_id ASC (FIFO preservation)
        for pkey in partition_groups:
            partition_groups[pkey].sort(
                key=lambda r: (
                    r.occurred_at.timestamp() if r.occurred_at else 0.0,
                    str(r.event_id),
                )
            )

        # Build scheduled items per partition
        scheduled_items: List[PriorityScheduledItem] = []
        breakdown: Dict[PriorityLevel, int] = defaultdict(int)
        aged_count = 0

        # Evaluate each partition's head event for inter-partition ranking
        partition_ranks: List[tuple] = []
        for pkey, records in partition_groups.items():
            head_record = records[0]
            base_prio = PriorityResolver.resolve_priority(head_record)
            eff_weight, is_aged = PriorityAgingEngine.calculate_effective_weight(
                record=head_record,
                base_priority=base_prio,
                now=context.current_time,
                config=context.config,
            )
            head_ts = head_record.occurred_at.timestamp() if head_record.occurred_at else 0.0

            # Sorting tuple for partition:
            # (-effective_weight, head_timestamp, partition_key)
            partition_ranks.append((eff_weight, head_ts, pkey, records))

        # Sort partitions: highest effective weight first, then earliest timestamp, then pkey
        partition_ranks.sort(key=lambda t: (-t[0], t[1], t[2]))

        # Flatten into final prioritized order
        all_prioritized_items: List[PriorityScheduledItem] = []
        for _, _, pkey, records in partition_ranks:
            for rec in records:
                base_prio = PriorityResolver.resolve_priority(rec)
                eff_weight, is_aged = PriorityAgingEngine.calculate_effective_weight(
                    record=rec,
                    base_priority=base_prio,
                    now=context.current_time,
                    config=context.config,
                )
                if is_aged:
                    aged_count += 1

                resolved_level = RANK_TO_PRIORITY.get(eff_weight, base_prio)
                breakdown[resolved_level] += 1

                ordering_policy = OrderingPolicyResolver.resolve(rec)
                trace_id = rec.trace_id or str(rec.correlation_id or rec.event_id)
                lock_timeout = 30.0  # default lock timeout

                item = PriorityScheduledItem(
                    event_id=rec.event_id,
                    partition_key=pkey,
                    ordering_policy=ordering_policy,
                    trace_id=trace_id,
                    lock_timeout_seconds=lock_timeout,
                    base_priority=base_prio,
                    effective_weight=eff_weight,
                    is_aged=is_aged,
                    record=rec,
                )
                all_prioritized_items.append(item)

        # Apply target batch size limit
        batch_limit = context.target_batch_size
        scheduled = all_prioritized_items[:batch_limit]
        deferred = all_prioritized_items[batch_limit:]

        return PriorityScheduledPlan(
            scheduled_items=scheduled,
            deferred_items=deferred,
            effective_priorities_breakdown=dict(breakdown),
            aged_items_count=aged_count,
        )
