"""
HunterOS Engage V1 - Abstract Milestone Rule Contract
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from app.domain.conversations.timeline.models import MilestoneType

if TYPE_CHECKING:
    from app.domain.conversations.timeline.context import ConversationTimelineContext
    from app.domain.conversations.timeline.models import TimelineMilestone


class AbstractMilestoneRule(ABC):
    """Abstract contract for all pluggable milestone detection rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique rule identifier."""
        pass

    @property
    @abstractmethod
    def milestone_type(self) -> MilestoneType:
        """Type of milestone evaluated by this rule."""
        pass

    @abstractmethod
    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        """Evaluates normalized events in context and returns a milestone if criteria are met."""
        pass
