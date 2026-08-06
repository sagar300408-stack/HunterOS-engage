"""
HunterOS Engage V1 - Abstract Insight View
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines the base contract for rendering perspective-specific insight views.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.domain.conversations.insight.models import ConversationInsightResult


class AbstractInsightView(ABC):
    """Abstract base class for insight view projections."""

    @property
    @abstractmethod
    def view_name(self) -> str:
        """Unique identifier for this projection view."""
        pass

    @abstractmethod
    def render(self, result: ConversationInsightResult, **kwargs: Any) -> Dict[str, Any]:
        """Renders the ConversationInsightResult into a targeted dictionary representation."""
        pass
