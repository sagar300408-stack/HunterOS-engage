"""
HunterOS Engage V1 - Abstract Pipeline Stage
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines the base contract for all 8 stages in the deterministic insight pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.conversations.insight.context import ConversationInsightContext


class InsightPipelineStage(ABC):
    """Abstract base class for all insight processing pipeline stages."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of this stage for diagnostics and execution tracking."""
        pass

    @abstractmethod
    def execute(self, context: ConversationInsightContext) -> None:
        """Executes stage logic and mutates context deterministically."""
        pass
