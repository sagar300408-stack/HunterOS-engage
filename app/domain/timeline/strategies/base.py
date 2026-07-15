from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel

from app.domain.timeline.models import TimelineSeverity
from app.events.model.base_event import UniversalBaseEvent


class TimelineFormattedData(BaseModel):
    """Result of formatting a timeline entry for display."""
    title: str
    description: str


class BaseTimelineStrategy(ABC):
    """
    Base strategy for converting an event into a Timeline Entry.
    It dictates default severity, extracts structured data, and formats text on the fly.
    """

    @property
    @abstractmethod
    def default_severity(self) -> TimelineSeverity:
        pass

    @property
    @abstractmethod
    def activity_type(self) -> str:
        """The logical type of this activity, e.g., 'conversation_reply'."""
        pass

    @abstractmethod
    def extract_structured_data(self, event: UniversalBaseEvent) -> Dict[str, Any]:
        """
        Extract only the variables necessary for displaying the event in the UI.
        Do NOT generate formatted strings here.
        """
        pass

    @abstractmethod
    def format_for_display(self, structured_data: Dict[str, Any]) -> TimelineFormattedData:
        """
        Convert structured data into human-readable text for API responses.
        This ensures UI text changes do not require database migrations.
        """
        pass
