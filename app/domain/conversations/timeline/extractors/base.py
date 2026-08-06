"""
HunterOS Engage V1 - Abstract Timeline Event Extractor Contract
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.conversations.timeline.context import ConversationTimelineContext
    from app.domain.conversations.timeline.models import TimelineEvent


class AbstractTimelineEventExtractor(ABC):
    """Abstract contract for all pluggable timeline event extractors."""

    @property
    @abstractmethod
    def extractor_name(self) -> str:
        """Unique identifier for this extractor."""
        pass

    @abstractmethod
    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        """Extracts deterministic timeline events from the analysis context."""
        pass
