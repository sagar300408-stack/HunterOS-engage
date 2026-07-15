from typing import Any, Dict

from app.domain.timeline.models import TimelineSeverity
from app.domain.timeline.strategies.base import BaseTimelineStrategy, TimelineFormattedData
from app.events.model.base_event import UniversalBaseEvent


class CustomerReplyProjectionStrategy(BaseTimelineStrategy):
    @property
    def default_severity(self) -> TimelineSeverity:
        return TimelineSeverity.NORMAL

    @property
    def activity_type(self) -> str:
        return "customer_replied"

    def extract_structured_data(self, event: UniversalBaseEvent) -> Dict[str, Any]:
        message_content = getattr(event, "message_content", "")
        return {
            "snippet": message_content[:100] + ("..." if len(message_content) > 100 else "")
        }

    def format_for_display(self, structured_data: Dict[str, Any]) -> TimelineFormattedData:
        return TimelineFormattedData(
            title="Customer replied to conversation",
            description=structured_data.get("snippet", "Customer sent a message.")
        )


class MeetingProjectionStrategy(BaseTimelineStrategy):
    @property
    def default_severity(self) -> TimelineSeverity:
        return TimelineSeverity.HIGH

    @property
    def activity_type(self) -> str:
        return "meeting_booked"

    def extract_structured_data(self, event: UniversalBaseEvent) -> Dict[str, Any]:
        return {
            "meeting_time": event.metadata.get("meeting_time"),
            "meeting_url": event.metadata.get("meeting_url")
        }

    def format_for_display(self, structured_data: Dict[str, Any]) -> TimelineFormattedData:
        time = structured_data.get("meeting_time", "Unknown time")
        return TimelineFormattedData(
            title="Meeting scheduled",
            description=f"A meeting was booked for {time}."
        )


class DefaultProjectionStrategy(BaseTimelineStrategy):
    """Fallback strategy for any event not explicitly registered."""
    
    @property
    def default_severity(self) -> TimelineSeverity:
        return TimelineSeverity.INFO

    @property
    def activity_type(self) -> str:
        return "system_event"

    def extract_structured_data(self, event: UniversalBaseEvent) -> Dict[str, Any]:
        return {
            "event_name": event.event_name,
            "category": event.category.value
        }

    def format_for_display(self, structured_data: Dict[str, Any]) -> TimelineFormattedData:
        event_name = structured_data.get("event_name", "Unknown Event")
        return TimelineFormattedData(
            title=f"System Activity: {event_name}",
            description="An internal system event was recorded."
        )
