"""
HunterOS Engage — Virtual Priority Aging Engine
app/events/priority/aging.py

Prevents starvation of lower-priority events under sustained high-priority load
by dynamically computing virtual scheduling weights.
The persistent database record priority is NEVER modified.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Tuple

from app.events.observability.metrics import event_metrics
from app.events.priority.config import PriorityConfig
from app.events.priority.priority import PriorityLevel, PriorityResolver
from app.events.store.models import EventRecord

logger = logging.getLogger(__name__)


class PriorityAgingEngine:
    """
    Computes virtual priority boosts for events waiting in the outbox.
    """

    @classmethod
    def calculate_effective_weight(
        cls,
        record: EventRecord,
        base_priority: PriorityLevel,
        now: datetime,
        config: PriorityConfig,
    ) -> Tuple[int, bool]:
        """
        Calculates the effective numerical scheduling weight (1..5) for an event.

        Returns:
            Tuple[effective_weight, is_aged]
        """
        base_rank = PriorityResolver.get_rank(base_priority)

        if not config.enable_priority_aging:
            return base_rank, False

        # Calculate wait time since event occurred
        occurred_at = record.occurred_at
        if occurred_at is None:
            return base_rank, False

        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        wait_seconds = max(0.0, (now - occurred_at).total_seconds())

        if wait_seconds < config.aging_threshold_seconds:
            return base_rank, False

        excess_seconds = wait_seconds - config.aging_threshold_seconds
        step_duration = max(1.0, config.aging_step_seconds)
        steps = int(excess_seconds // step_duration) + 1
        boost = min(config.max_aging_boost, steps)

        effective_rank = min(5, base_rank + boost)
        is_aged = effective_rank > base_rank

        if is_aged:
            event_metrics.increment("priority_aging_promotions")
            logger.debug(
                f"Priority aging applied to event {record.event_id}: "
                f"base={base_priority.value}({base_rank}) -> effective_weight={effective_rank} "
                f"(waited {wait_seconds:.1f}s)"
            )

        return effective_rank, is_aged
