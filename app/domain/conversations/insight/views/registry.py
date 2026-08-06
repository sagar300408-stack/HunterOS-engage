"""
HunterOS Engage V1 - Insight View Registry
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Registry for managing and executing insight projection view renderers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.domain.conversations.insight.models import ConversationInsightResult
from app.domain.conversations.insight.views.base import AbstractInsightView

logger = logging.getLogger(__name__)


class InsightViewRegistry:
    """Registry coordinating all registered insight projection views."""

    def __init__(self) -> None:
        self._views: Dict[str, AbstractInsightView] = {}

    def register(self, view: AbstractInsightView) -> None:
        """Registers an insight view projection."""
        self._views[view.view_name] = view
        logger.debug("Registered InsightView: %s", view.view_name)

    def unregister(self, view_name: str) -> Optional[AbstractInsightView]:
        """Unregisters an insight view."""
        return self._views.pop(view_name, None)

    def get(self, view_name: str) -> Optional[AbstractInsightView]:
        """Retrieves a view by name."""
        return self._views.get(view_name)

    def list_views(self) -> List[str]:
        """Returns names of all registered views."""
        return list(self._views.keys())

    def render_view(
        self,
        view_name: str,
        result: ConversationInsightResult,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Renders an insight result using the specified view."""
        renderer = self.get(view_name)
        if not renderer:
            raise KeyError(f"Insight view '{view_name}' is not registered. Available: {self.list_views()}")
        return renderer.render(result, **kwargs)


default_insight_view_registry = InsightViewRegistry()
