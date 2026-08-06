"""
HunterOS Engage V1 - Abstract Risk Detector
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines the base contract for pluggable risk detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Set

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import InsightCategory, RiskInsight


class AbstractRiskDetector(ABC):
    """Abstract base class for all risk detection rules."""

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Unique identifier for this risk detector."""
        pass

    @property
    @abstractmethod
    def supported_categories(self) -> Set[InsightCategory]:
        """Categories of risks this detector can identify."""
        pass

    @abstractmethod
    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        """
        Executes deterministic evaluation against conversation artifacts
        and returns identified risk insights with full lineage evidence.
        """
        pass
