"""
HunterOS Engage V1 - Timeline View Registry
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Extensible registry managing timeline projection view renderers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.conversations.timeline.views.base import AbstractTimelineView
from app.domain.conversations.timeline.views.standard import (
    ChronologicalEventView,
    ExecutiveSummaryTimelineView,
    ImportantMomentsView,
    MilestoneOnlyView,
    ParticipantSpecificView,
)

logger = logging.getLogger(__name__)


class TimelineViewRegistry:
    """Registry maintaining and rendering pluggable timeline projection views."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._views: Dict[str, AbstractTimelineView] = {}
        if register_defaults:
            self._register_default_views()

    def _register_default_views(self) -> None:
        defaults: List[AbstractTimelineView] = [
            ChronologicalEventView(),
            MilestoneOnlyView(),
            ImportantMomentsView(),
            ExecutiveSummaryTimelineView(),
            ParticipantSpecificView(),
        ]
        for view in defaults:
            self.register(view)

    def register(self, view: AbstractTimelineView) -> None:
        """Registers a timeline projection view."""
        self._views[view.view_name] = view
        logger.debug("Registered timeline view: %s", view.view_name)

    def unregister(self, view_name: str) -> Optional[AbstractTimelineView]:
        """Removes a view from the registry."""
        return self._views.pop(view_name, None)

    def get(self, view_name: str) -> Optional[AbstractTimelineView]:
        """Retrieves a view by name."""
        return self._views.get(view_name)

    def list_views(self) -> List[str]:
        """Returns all registered view names."""
        return list(self._views.keys())

    def render_view(self, view_name: str, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        """Renders the specified timeline view projection."""
        view = self.get(view_name)
        if not view:
            raise KeyError(f"Timeline view '{view_name}' is not registered. Available views: {self.list_views()}")
        return view.render(timeline, **kwargs)


# Global default singleton instance
default_timeline_view_registry = TimelineViewRegistry()
