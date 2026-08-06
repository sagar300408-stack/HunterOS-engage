"""
HunterOS Engage V1 - Abstract Opportunity Detector
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines the base contract for pluggable opportunity detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Set

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.models import InsightCategory, OpportunityInsight


class AbstractOpportunityDetector(ABC):
    """Abstract base class for all commercial and operational opportunity rules."""

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Unique identifier for this opportunity detector."""
        pass

    @property
    @abstractmethod
    def supported_categories(self) -> Set[InsightCategory]:
        """Categories of opportunities this detector identifies."""
        pass

    @abstractmethod
    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        """
        Executes deterministic evaluation against conversation artifacts
        and returns identified opportunity insights with full lineage evidence.
        """
        pass
