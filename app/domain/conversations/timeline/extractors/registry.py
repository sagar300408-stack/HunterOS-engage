"""
HunterOS Engage V1 - Timeline Event Extractor Registry
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Extensible registry orchestrating all timeline event extractors.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.extractors.base import AbstractTimelineEventExtractor
from app.domain.conversations.timeline.extractors.standard import (
    AgreementEventExtractor,
    BudgetEventExtractor,
    CustomerIntroEventExtractor,
    CustomTimelineEventExtractor,
    DateEventExtractor,
    DocumentEventExtractor,
    FollowUpEventExtractor,
    InformationSharedEventExtractor,
    LifecycleEventExtractor,
    MeetingEventExtractor,
    ObjectionEventExtractor,
    QuestionEventExtractor,
    RequirementEventExtractor,
)
from app.domain.conversations.timeline.models import TimelineEvent

logger = logging.getLogger(__name__)


class TimelineEventExtractorRegistry:
    """Registry maintaining and orchestrating pluggable timeline event extractors."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._extractors: Dict[str, AbstractTimelineEventExtractor] = {}
        if register_defaults:
            self._register_default_extractors()

    def _register_default_extractors(self) -> None:
        """Registers the 12 standard business timeline event extractors."""
        defaults: List[AbstractTimelineEventExtractor] = [
            LifecycleEventExtractor(),
            CustomerIntroEventExtractor(),
            RequirementEventExtractor(),
            BudgetEventExtractor(),
            DateEventExtractor(),
            DocumentEventExtractor(),
            MeetingEventExtractor(),
            QuestionEventExtractor(),
            InformationSharedEventExtractor(),
            ObjectionEventExtractor(),
            AgreementEventExtractor(),
            FollowUpEventExtractor(),
            CustomTimelineEventExtractor(),
        ]
        for extractor in defaults:
            self.register(extractor)

    def register(self, extractor: AbstractTimelineEventExtractor) -> None:
        """Registers a timeline event extractor."""
        self._extractors[extractor.extractor_name] = extractor
        logger.debug("Registered timeline event extractor: %s", extractor.extractor_name)

    def unregister(self, extractor_name: str) -> Optional[AbstractTimelineEventExtractor]:
        """Removes an extractor from the registry."""
        return self._extractors.pop(extractor_name, None)

    def get(self, extractor_name: str) -> Optional[AbstractTimelineEventExtractor]:
        """Retrieves an extractor by name."""
        return self._extractors.get(extractor_name)

    def list_extractors(self) -> List[str]:
        """Returns all registered extractor names."""
        return list(self._extractors.keys())

    def extract_all(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        """Runs all registered extractors against the context and returns accumulated events."""
        all_events: List[TimelineEvent] = []
        for name, extractor in self._extractors.items():
            try:
                extracted = extractor.extract(context)
                all_events.extend(extracted)
            except Exception as e:
                logger.error("Error in timeline extractor %s: %s", name, str(e), exc_info=True)
                context.add_warning(f"Extractor {name} failed: {str(e)}")
        return all_events


# Global default singleton instance
default_timeline_event_extractor_registry = TimelineEventExtractorRegistry()
