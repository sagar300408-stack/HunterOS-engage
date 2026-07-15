from typing import Optional
from uuid import UUID

from pydantic import Field

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory


class MeetingBookedEvent(UniversalBaseEvent):
    """Event emitted when a meeting is booked."""
    category: EventCategory = Field(default=EventCategory.SCHEDULING, frozen=True)
    event_name: str = Field(default="MeetingBookedEvent", frozen=True)

    def __init__(self, meeting_time: str, meeting_url: Optional[str] = None, duration_minutes: int = 30, **kwargs):
        # We store these specific payload attributes into `metadata` natively
        metadata = kwargs.get("metadata", {})
        metadata["meeting_time"] = meeting_time
        if meeting_url:
            metadata["meeting_url"] = meeting_url
        metadata["duration_minutes"] = duration_minutes
        kwargs["metadata"] = metadata
        super().__init__(**kwargs)
