"""
HunterOS Engage — Adaptive Backpressure & Flow Control Engine
app/events/priority/flow_control.py

Regulates dispatch throughput and selectively throttles lower-priority events
during elevated load states (BUSY, HIGH_LOAD, SATURATED) while unconditionally
protecting CRITICAL traffic and in-flight retries/replays.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.events.observability.metrics import event_metrics
from app.events.priority.config import PriorityConfig
from app.events.priority.context import PriorityScheduledItem, PriorityScheduledPlan
from app.events.priority.health import QueueHealthSnapshot
from app.events.priority.priority import PriorityLevel

logger = logging.getLogger(__name__)


class SystemLoadState(str, Enum):
    NORMAL = "NORMAL"
    BUSY = "BUSY"
    HIGH_LOAD = "HIGH_LOAD"
    SATURATED = "SATURATED"


@dataclass(frozen=True)
class FlowControlledDispatchPlan:
    """
    Final actionable dispatch plan produced after applying adaptive flow control and backpressure.
    """
    dispatches_to_execute: List[PriorityScheduledItem] = field(default_factory=list)
    deferred_dispatches: List[PriorityScheduledItem] = field(default_factory=list)
    throttled_count: int = 0
    effective_batch_size: int = 50
    load_state: SystemLoadState = SystemLoadState.NORMAL
    backpressure_active: bool = False


class FlowController:
    """
    Adaptive Flow Controller and Overload Protection Engine.
    """

    def __init__(self, config: Optional[PriorityConfig] = None):
        self.config = config or PriorityConfig.from_env()

    def apply_flow_control(
        self,
        plan: PriorityScheduledPlan,
        health: Optional[QueueHealthSnapshot] = None,
        base_batch_size: int = 50,
    ) -> FlowControlledDispatchPlan:
        """
        Filters and throttles scheduled items based on current system load state.
        """
        if not self.config.enable_backpressure or health is None:
            return FlowControlledDispatchPlan(
                dispatches_to_execute=list(plan.scheduled_items),
                deferred_dispatches=list(plan.deferred_items),
                throttled_count=0,
                effective_batch_size=base_batch_size,
                load_state=SystemLoadState.NORMAL,
                backpressure_active=False,
            )

        load_state_str = health.system_load_state
        try:
            load_state = SystemLoadState(load_state_str)
        except ValueError:
            load_state = SystemLoadState.NORMAL

        # Determine Batch Size Multiplier
        if load_state == SystemLoadState.SATURATED:
            batch_multiplier = 0.25
        elif load_state == SystemLoadState.HIGH_LOAD:
            batch_multiplier = 0.5
        elif load_state == SystemLoadState.BUSY:
            batch_multiplier = 0.8
        else:
            batch_multiplier = 1.0

        effective_batch_size = max(1, int(base_batch_size * batch_multiplier))
        backpressure_active = load_state in (
            SystemLoadState.BUSY,
            SystemLoadState.HIGH_LOAD,
            SystemLoadState.SATURATED,
        )

        if backpressure_active:
            event_metrics.increment("dispatcher_backpressure_events")

        dispatches: List[PriorityScheduledItem] = []
        deferred: List[PriorityScheduledItem] = list(plan.deferred_items)
        throttled_count = 0

        for item in plan.scheduled_items:
            rec = item.record
            is_retry = rec.lifecycle_state == "RETRYING"
            is_replay = bool(
                isinstance(rec.metadata_payload, dict)
                and rec.metadata_payload.get("is_replay")
            )

            # Invariant: Retries, Replays, and CRITICAL traffic are NEVER throttled
            if is_retry or is_replay or item.base_priority == PriorityLevel.CRITICAL:
                dispatches.append(item)
                continue

            # Invariant: Under SATURATED load state, shed NORMAL, LOW, BACKGROUND
            if load_state == SystemLoadState.SATURATED:
                if item.base_priority in (
                    PriorityLevel.NORMAL,
                    PriorityLevel.LOW,
                    PriorityLevel.BACKGROUND,
                ):
                    deferred.append(item)
                    throttled_count += 1
                    event_metrics.increment("dispatcher_throttled_events")
                    continue
                else:
                    dispatches.append(item)
                    continue

            # Invariant: Under HIGH_LOAD load state, shed LOW and BACKGROUND
            if load_state == SystemLoadState.HIGH_LOAD:
                if item.base_priority in (
                    PriorityLevel.LOW,
                    PriorityLevel.BACKGROUND,
                ):
                    deferred.append(item)
                    throttled_count += 1
                    event_metrics.increment("dispatcher_throttled_events")
                    continue
                else:
                    dispatches.append(item)
                    continue

            # NORMAL and BUSY accept all priorities up to effective batch limit
            dispatches.append(item)

        # Apply effective batch limit to accepted dispatches
        final_dispatches = dispatches[:effective_batch_size]
        final_deferred = dispatches[effective_batch_size:] + deferred

        return FlowControlledDispatchPlan(
            dispatches_to_execute=final_dispatches,
            deferred_dispatches=final_deferred,
            throttled_count=throttled_count,
            effective_batch_size=effective_batch_size,
            load_state=load_state,
            backpressure_active=backpressure_active,
        )
