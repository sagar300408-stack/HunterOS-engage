"""
HunterOS Engage V1 - Chronological Ordering Stage
Phase 2.2.2: Conversation Intelligence - Conversation Timeline
"""

from __future__ import annotations

import logging
from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import (
    TimelineEvent,
    TimelinePipelineState,
)
from app.domain.conversations.timeline.stages.base import TimelinePipelineStage

logger = logging.getLogger(__name__)


class ChronologicalOrderingStage(TimelinePipelineStage):
    """Sorts all normalized events chronologically, assigns sequential indices and computes relative offsets."""

    @property
    def stage_name(self) -> str:
        return "ChronologicalOrderingStage"

    def execute(self, context: ConversationTimelineContext) -> None:
        context.transition_to(TimelinePipelineState.ORDERING)

        events = list(context.normalized_events)
        if not events:
            return

        # Sort strictly ascending by timestamp
        events.sort(key=lambda e: e.occurred_at)

        base_time = events[0].occurred_at
        ordered_events: list[TimelineEvent] = []

        for idx, ev in enumerate(events):
            offset = max(0.0, (ev.occurred_at - base_time).total_seconds())
            indexed_ev = TimelineEvent(
                event_id=ev.event_id,
                conversation_id=ev.conversation_id,
                workspace_id=ev.workspace_id,
                event_type=ev.event_type,
                category=ev.category,
                title=ev.title,
                description=ev.description,
                occurred_at=ev.occurred_at,
                sequence_index=idx,
                time_offset_seconds=round(offset, 3),
                provenance=ev.provenance,
                confidence=ev.confidence,
                metadata=ev.metadata,
                created_at=ev.created_at,
            )
            ordered_events.append(indexed_ev)

        context.set_normalized_events(ordered_events)

        logger.debug(
            "Chronologically ordered %d events for conversation %s",
            len(ordered_events),
            context.conversation_id,
        )
