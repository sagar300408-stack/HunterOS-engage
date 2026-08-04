"""
Ordering Policy Framework for HunterOS Engage.

Defines execution ordering policies and the precedence resolver:
    Precedence Order:
        1. metadata["ordering_policy"] (explicit override in event metadata)
        2. event_class.ordering_policy (declarative attribute on event class/instance)
        3. category default (derived from EventCategory)

Policies:
    - ORDERED: Strict FIFO execution inside a partition. Only one worker processes
      a given partition at any time.
    - UNORDERED: Can execute immediately in parallel across workers without partition locks.
    - CONFIGURABLE: Marker indicating the policy is dynamically determined by context.
"""

from enum import Enum
from typing import Any, Optional, Set, Union

from app.events.model.categories import EventCategory


class OrderingPolicy(str, Enum):
    """
    Execution ordering policy for events.
    """
    ORDERED = "ORDERED"
    UNORDERED = "UNORDERED"
    CONFIGURABLE = "CONFIGURABLE"


# Default Category Mappings
ORDERED_CATEGORIES: Set[EventCategory] = {
    EventCategory.CONVERSATION,
    EventCategory.CUSTOMER,
    EventCategory.CRM,
    EventCategory.FOLLOWUP,
    EventCategory.LEAD,
    EventCategory.MEETING,
    EventCategory.SCHEDULING,
    EventCategory.AUTOMATION,
    EventCategory.ACTION,
    EventCategory.APPROVAL,
    EventCategory.AUTONOMOUS,
}

UNORDERED_CATEGORIES: Set[EventCategory] = {
    EventCategory.ANALYTICS,
    EventCategory.AUDIT,
    EventCategory.NOTIFICATION,
    EventCategory.PLATFORM,
    EventCategory.RESEARCH,
    EventCategory.PROPOSAL,
    EventCategory.AI_DECISION,
    EventCategory.FRICTION,
    EventCategory.SLA,
    EventCategory.INTEGRATION,
    EventCategory.MARKETPLACE,
}


class OrderingPolicyResolver:
    """
    Resolves the effective OrderingPolicy for any event or record according to precedence rules.
    """

    @classmethod
    def resolve(cls, event_or_record: Any) -> OrderingPolicy:
        """
        Resolves OrderingPolicy using strict precedence:
            1. metadata["ordering_policy"]
            2. event_class.ordering_policy (or instance attribute)
            3. category default

        Args:
            event_or_record: Domain event instance, EventRecord, or dict.

        Returns:
            OrderingPolicy (ORDERED or UNORDERED).
        """
        # 1. Metadata check
        metadata = cls._extract_metadata(event_or_record)
        if isinstance(metadata, dict) and "ordering_policy" in metadata:
            raw_policy = metadata["ordering_policy"]
            parsed = cls._parse_policy(raw_policy)
            if parsed and parsed != OrderingPolicy.CONFIGURABLE:
                return parsed

        # 2. Event class / instance attribute check
        if hasattr(event_or_record, "ordering_policy"):
            raw_policy = getattr(event_or_record, "ordering_policy")
            parsed = cls._parse_policy(raw_policy)
            if parsed and parsed != OrderingPolicy.CONFIGURABLE:
                return parsed

        # Check if the class of the object has ordering_policy
        obj_class = getattr(event_or_record, "__class__", None)
        if obj_class and hasattr(obj_class, "ordering_policy"):
            raw_policy = getattr(obj_class, "ordering_policy")
            parsed = cls._parse_policy(raw_policy)
            if parsed and parsed != OrderingPolicy.CONFIGURABLE:
                return parsed

        # 3. Category default
        category = cls._extract_category(event_or_record)
        if category:
            if category in ORDERED_CATEGORIES:
                return OrderingPolicy.ORDERED
            if category in UNORDERED_CATEGORIES:
                return OrderingPolicy.UNORDERED

        # Global default for safety is ORDERED (fail-safe for business consistency)
        return OrderingPolicy.ORDERED

    @classmethod
    def _extract_metadata(cls, obj: Any) -> Optional[dict]:
        """Extracts metadata dictionary from object."""
        if isinstance(obj, dict):
            return obj.get("metadata") or obj.get("metadata_payload")
        if hasattr(obj, "metadata") and isinstance(obj.metadata, dict):
            return obj.metadata
        if hasattr(obj, "metadata_payload") and isinstance(obj.metadata_payload, dict):
            return obj.metadata_payload
        return None

    @classmethod
    def _extract_category(cls, obj: Any) -> Optional[EventCategory]:
        """Extracts EventCategory from object."""
        raw_cat = None
        if isinstance(obj, dict):
            raw_cat = obj.get("category")
        elif hasattr(obj, "category"):
            raw_cat = getattr(obj, "category")

        if isinstance(raw_cat, EventCategory):
            return raw_cat
        if isinstance(raw_cat, str):
            try:
                return EventCategory(raw_cat)
            except ValueError:
                return None
        return None

    @classmethod
    def _parse_policy(cls, val: Any) -> Optional[OrderingPolicy]:
        """Parses a policy value to OrderingPolicy."""
        if isinstance(val, OrderingPolicy):
            return val
        if isinstance(val, str):
            try:
                return OrderingPolicy(val.upper().strip())
            except ValueError:
                return None
        return None
