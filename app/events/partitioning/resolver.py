"""
Partition Resolution Engine for HunterOS Engage.

Deterministically resolves every EventRecord or domain event to exactly one partition key.

Priority resolution hierarchy:
    1. Explicit metadata partition_key (if provided)
    2. conversation_id  -> "conversation:{conversation_id}"
    3. customer_id      -> "customer:{customer_id}"
    4. workspace_id     -> "workspace:{workspace_id}"
    5. event_id         -> "event:{event_id}"

Invariants:
    - Partition assignment is strictly deterministic and collision-resistant.
    - The same logical entity always resolves to the same partition.
    - Supports UniversalBaseEvent instances, EventRecord models, and raw dictionary payloads.
"""

from typing import Any, Optional, Union
from uuid import UUID

from app.events.model.base_event import UniversalBaseEvent
from app.events.store.models import EventRecord


class PartitionResolver:
    """
    Deterministic Partition Resolution Engine.
    """

    @classmethod
    def resolve_partition_key(cls, event_or_record: Union[UniversalBaseEvent, EventRecord, dict, Any]) -> str:
        """
        Resolves the authoritative partition key for a domain event, EventRecord, or dict.

        Args:
            event_or_record: Domain event instance, EventRecord database model, or dict.

        Returns:
            Deterministic partition key string (e.g. 'conversation:123e4567-e89b-12d3-a456-426614174000').
        """
        # 1. Check for explicit metadata override
        metadata = cls._extract_field(event_or_record, "metadata", "metadata_payload")
        if isinstance(metadata, dict):
            explicit_key = metadata.get("partition_key") or metadata.get("explicit_partition_key")
            if explicit_key:
                return str(explicit_key).strip()

        # Check direct partition_key attribute if already populated
        existing_key = cls._extract_field(event_or_record, "partition_key")
        if existing_key:
            return str(existing_key).strip()

        # 2. Priority: conversation_id
        conversation_id = cls._extract_field(event_or_record, "conversation_id")
        if conversation_id:
            return f"conversation:{cls._format_id(conversation_id)}"

        # 3. Priority: customer_id
        customer_id = cls._extract_field(event_or_record, "customer_id")
        if customer_id:
            return f"customer:{cls._format_id(customer_id)}"

        # 4. Priority: workspace_id
        workspace_id = cls._extract_field(event_or_record, "workspace_id")
        if workspace_id:
            return f"workspace:{cls._format_id(workspace_id)}"

        # 5. Fallback: event_id
        event_id = cls._extract_field(event_or_record, "event_id")
        if event_id:
            return f"event:{cls._format_id(event_id)}"

        # Absolute fallback if somehow an empty record is passed
        return "partition:default"

    @classmethod
    def _extract_field(cls, obj: Any, *field_names: str) -> Optional[Any]:
        """Safely extracts the first non-null field value from object or dict."""
        for field in field_names:
            if isinstance(obj, dict):
                val = obj.get(field)
                if val is not None and str(val).strip():
                    return val
            elif hasattr(obj, field):
                val = getattr(obj, field)
                if val is not None and str(val).strip():
                    return val
        return None

    @classmethod
    def _format_id(cls, value: Union[UUID, str, Any]) -> str:
        """Formats a UUID or string identifier consistently."""
        if isinstance(value, UUID):
            return str(value).lower()
        return str(value).strip().lower()
