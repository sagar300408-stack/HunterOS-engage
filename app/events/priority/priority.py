"""
HunterOS Engage — Priority Framework
app/events/priority/priority.py

Defines standard priority levels, numeric ranks, and deterministic priority
resolution with multi-tier precedence:
    metadata["priority"] -> event.priority -> category default -> NORMAL
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, Optional, Union

from app.events.model.categories import EventCategory

logger = logging.getLogger(__name__)


class PriorityLevel(str, Enum):
    """
    Standardized operational priority levels for event scheduling.
    Higher rank denotes higher scheduling urgency.
    """
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


PRIORITY_RANKS: Dict[PriorityLevel, int] = {
    PriorityLevel.CRITICAL: 5,
    PriorityLevel.HIGH: 4,
    PriorityLevel.NORMAL: 3,
    PriorityLevel.LOW: 2,
    PriorityLevel.BACKGROUND: 1,
}

RANK_TO_PRIORITY: Dict[int, PriorityLevel] = {
    v: k for k, v in PRIORITY_RANKS.items()
}

# Categorical defaults for all platform event categories
DEFAULT_CATEGORY_PRIORITIES: Dict[Union[EventCategory, str], PriorityLevel] = {
    # Real-time / Critical conversational streams
    EventCategory.CONVERSATION: PriorityLevel.HIGH,
    EventCategory.APPROVAL: PriorityLevel.HIGH,
    EventCategory.ACTION: PriorityLevel.HIGH,
    EventCategory.SLA: PriorityLevel.HIGH,
    EventCategory.FRICTION: PriorityLevel.HIGH,

    # Core business domain operations
    EventCategory.CUSTOMER: PriorityLevel.NORMAL,
    EventCategory.CRM: PriorityLevel.NORMAL,
    EventCategory.FOLLOWUP: PriorityLevel.NORMAL,
    EventCategory.MEETING: PriorityLevel.NORMAL,
    EventCategory.SCHEDULING: PriorityLevel.NORMAL,
    EventCategory.LEAD: PriorityLevel.NORMAL,
    EventCategory.AUTOMATION: PriorityLevel.NORMAL,
    EventCategory.AUTONOMOUS: PriorityLevel.NORMAL,
    EventCategory.AI_DECISION: PriorityLevel.NORMAL,
    EventCategory.INTEGRATION: PriorityLevel.NORMAL,
    EventCategory.PROPOSAL: PriorityLevel.NORMAL,
    EventCategory.PLATFORM: PriorityLevel.NORMAL,
    EventCategory.MARKETPLACE: PriorityLevel.NORMAL,

    # Asynchronous / Non-urgent notifications & research
    EventCategory.RESEARCH: PriorityLevel.LOW,
    EventCategory.NOTIFICATION: PriorityLevel.LOW,

    # Background analytics & audit logging
    EventCategory.ANALYTICS: PriorityLevel.BACKGROUND,
    EventCategory.AUDIT: PriorityLevel.BACKGROUND,
}


class PriorityResolver:
    """
    Deterministic priority resolution engine.
    Applies strict priority precedence:
        1. Explicit metadata override (metadata["priority"] or metadata_payload["priority"])
        2. Event-level class or instance attribute (event.priority)
        3. Event category default mapping
        4. Global fallback (PriorityLevel.NORMAL)
    """

    @classmethod
    def resolve_priority(cls, event: Any) -> PriorityLevel:
        """
        Resolves the operational PriorityLevel for a domain event, EventRecord, or dictionary.
        """
        # 1. Check Metadata Overrides
        metadata = None
        if hasattr(event, "metadata_payload") and isinstance(event.metadata_payload, dict):
            metadata = event.metadata_payload
        elif hasattr(event, "metadata") and isinstance(event.metadata, dict):
            metadata = event.metadata
        elif isinstance(event, dict):
            metadata = event.get("metadata_payload") or event.get("metadata") or {}

        if metadata:
            raw_meta_priority = metadata.get("priority")
            if raw_meta_priority:
                resolved = cls._parse_priority_value(raw_meta_priority)
                if resolved:
                    return resolved

        # 2. Check Event Object Attribute (event.priority)
        if hasattr(event, "priority"):
            raw_attr_priority = getattr(event, "priority")
            if raw_attr_priority is not None:
                resolved = cls._parse_priority_value(raw_attr_priority)
                if resolved:
                    return resolved
        elif isinstance(event, dict) and "priority" in event and event["priority"] is not None:
            resolved = cls._parse_priority_value(event["priority"])
            if resolved:
                return resolved

        # 3. Check Event Category Default
        category = getattr(event, "category", None)
        if category is None and isinstance(event, dict):
            category = event.get("category")

        if category is not None:
            cat_enum = None
            if isinstance(category, EventCategory):
                cat_enum = category
            elif isinstance(category, str):
                try:
                    cat_enum = EventCategory(category.upper())
                except ValueError:
                    pass

            if cat_enum and cat_enum in DEFAULT_CATEGORY_PRIORITIES:
                return DEFAULT_CATEGORY_PRIORITIES[cat_enum]

        # 4. Fallback to NORMAL
        return PriorityLevel.NORMAL

    @classmethod
    def get_rank(cls, priority: Union[PriorityLevel, str, int]) -> int:
        """Returns the numeric rank (1..5) for a PriorityLevel."""
        if isinstance(priority, int):
            return max(1, min(5, priority))
        if isinstance(priority, str):
            try:
                priority = PriorityLevel(priority.upper())
            except ValueError:
                return PRIORITY_RANKS[PriorityLevel.NORMAL]
        return PRIORITY_RANKS.get(priority, PRIORITY_RANKS[PriorityLevel.NORMAL])

    @classmethod
    def from_rank(cls, rank: int) -> PriorityLevel:
        """Returns the PriorityLevel corresponding to a numeric rank."""
        clamped_rank = max(1, min(5, rank))
        return RANK_TO_PRIORITY.get(clamped_rank, PriorityLevel.NORMAL)

    @classmethod
    def _parse_priority_value(cls, val: Any) -> Optional[PriorityLevel]:
        if isinstance(val, PriorityLevel):
            return val
        if isinstance(val, str):
            val_upper = val.strip().upper()
            try:
                return PriorityLevel(val_upper)
            except ValueError:
                pass
        elif isinstance(val, int):
            return cls.from_rank(val)
        return None
