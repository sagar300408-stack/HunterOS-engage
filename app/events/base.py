"""Base event dataclass for all HunterOS domain events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class BaseEvent:
    """
    All domain events inherit from BaseEvent.

    Every event carries a unique ID and a precise timestamp,
    making them safe to store, replay, or ship to a message broker.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
