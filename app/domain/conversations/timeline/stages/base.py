"""
HunterOS Engage V1 - Abstract Timeline Pipeline Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.conversations.timeline.context import ConversationTimelineContext


class TimelinePipelineStage(ABC):
    """Abstract contract for an independent, testable pipeline stage."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of the stage for telemetry and diagnostics."""
        pass

    @abstractmethod
    def execute(self, context: ConversationTimelineContext) -> None:
        """Executes stage logic against the execution context in-place."""
        pass
