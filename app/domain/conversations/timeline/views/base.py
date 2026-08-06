"""
HunterOS Engage V1 - Abstract Timeline View Contract
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, TYPE_CHECKING

from app.domain.conversations.timeline.models import TimelineViewFormat

if TYPE_CHECKING:
    from app.domain.conversations.timeline.models import ConversationTimeline


class AbstractTimelineView(ABC):
    """Abstract contract for all pluggable timeline projection views."""

    @property
    @abstractmethod
    def view_name(self) -> str:
        """Unique identifier for this view projection."""
        pass

    @property
    @abstractmethod
    def view_format(self) -> TimelineViewFormat:
        """Format format category produced by this view."""
        pass

    @abstractmethod
    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        """Renders the timeline into the structured projection dictionary."""
        pass
