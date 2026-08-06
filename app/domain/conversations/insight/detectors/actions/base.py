"""
HunterOS Engage V1 - Abstract Action Item Detector
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines the base contract for pluggable action item detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Set

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import ActionItemInsight, InsightCategory


class AbstractActionItemDetector(ABC):
    """Abstract base class for detecting explicit and directly implied action items."""

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Unique identifier for this action item detector."""
        pass

    @property
    @abstractmethod
    def supported_categories(self) -> Set[InsightCategory]:
        """Categories of action items this detector identifies."""
        pass

    @abstractmethod
    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        """
        Executes deterministic evaluation against conversation artifacts
        and returns identified action item insights with full lineage evidence.
        """
        pass
