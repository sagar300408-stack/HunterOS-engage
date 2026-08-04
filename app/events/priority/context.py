"""
HunterOS Engage — Scheduling Context & Plan Models
app/events/priority/context.py

Defines immutable, cohesive scheduling context passed to the PriorityScheduler,
as well as the priority-scheduled output plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from app.events.partitioning.ordering import OrderingPolicy
from app.events.partitioning.scheduler import PartitionDispatchPlan
from app.events.priority.config import PriorityConfig
from app.events.priority.priority import PriorityLevel
from app.events.store.models import EventRecord


@dataclass(frozen=True)
class PriorityScheduledItem:
    """
    Individual event dispatch scheduled by the priority scheduler with priority metadata.
    """
    event_id: UUID
    partition_key: str
    ordering_policy: OrderingPolicy
    trace_id: str
    lock_timeout_seconds: float
    base_priority: PriorityLevel
    effective_weight: int
    is_aged: bool
    record: EventRecord


@dataclass(frozen=True)
class PriorityScheduledPlan:
    """
    Immutable plan returned by AbstractPriorityScheduler.plan(context).
    """
    scheduled_items: List[PriorityScheduledItem] = field(default_factory=list)
    deferred_items: List[PriorityScheduledItem] = field(default_factory=list)
    effective_priorities_breakdown: Dict[PriorityLevel, int] = field(default_factory=dict)
    aged_items_count: int = 0

    @property
    def total_scheduled(self) -> int:
        return len(self.scheduled_items)

    @property
    def total_deferred(self) -> int:
        return len(self.deferred_items)


@dataclass(frozen=True)
class SchedulingContext:
    """
    Immutable, unified scheduling context encapsulating all inputs required
    for deterministic priority planning and flow control.
    """
    candidate_records: List[EventRecord]
    partition_plan: Optional[PartitionDispatchPlan] = None
    queue_health: Optional[Any] = None  # QueueHealthSnapshot
    load_state: str = "NORMAL"
    metrics_snapshot: Optional[Any] = None  # MetricsSnapshot
    active_partitions: Set[str] = field(default_factory=set)
    locked_partitions: Set[str] = field(default_factory=set)
    retry_backlog_count: int = 0
    replay_backlog_count: int = 0
    config: PriorityConfig = field(default_factory=PriorityConfig.from_env)
    current_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    target_batch_size: int = 50
