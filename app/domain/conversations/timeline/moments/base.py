"""
HunterOS Engage V1 - Abstract Important Moment Rule Contract
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from app.domain.conversations.timeline.models import ImportantMomentType

if TYPE_CHECKING:
    from app.domain.conversations.timeline.context import ConversationTimelineContext
    from app.domain.conversations.timeline.models import ImportantMoment


class AbstractImportantMomentRule(ABC):
    """Abstract contract for pluggable important moment detection rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique rule identifier."""
        pass

    @property
    @abstractmethod
    def moment_type(self) -> ImportantMomentType:
        """Type of important moment evaluated by this rule."""
        pass

    @abstractmethod
    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        """Evaluates conversation events in context and returns an ImportantMoment if criteria match."""
        pass
