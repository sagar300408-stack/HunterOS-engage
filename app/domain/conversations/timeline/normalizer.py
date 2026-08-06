"""
HunterOS Engage V1 - Timeline Event Normalizer
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic normalization of timeline events, timestamp standardizations,
deduplication, and metadata canonicalization.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from app.domain.conversations.timeline.models import (
    TimelineEvent,
    TimelineEventCategory,
    TimelineEventType,
)

logger = logging.getLogger(__name__)

EVENT_TYPE_TO_CATEGORY_MAP: Dict[TimelineEventType, TimelineEventCategory] = {
    TimelineEventType.CONVERSATION_STARTED: TimelineEventCategory.LIFECYCLE,
    TimelineEventType.CUSTOMER_INTRODUCED: TimelineEventCategory.COMMUNICATION,
    TimelineEventType.REQUIREMENT_IDENTIFIED: TimelineEventCategory.REQUIREMENT,
    TimelineEventType.QUESTION_ASKED: TimelineEventCategory.COMMUNICATION,
    TimelineEventType.INFORMATION_SHARED: TimelineEventCategory.COMMUNICATION,
    TimelineEventType.BUDGET_MENTIONED: TimelineEventCategory.FINANCIAL,
    TimelineEventType.DATE_MENTIONED: TimelineEventCategory.SCHEDULING,
    TimelineEventType.DOCUMENT_SHARED: TimelineEventCategory.DOCUMENT,
    TimelineEventType.MEETING_SCHEDULED: TimelineEventCategory.SCHEDULING,
    TimelineEventType.MEETING_COMPLETED: TimelineEventCategory.SCHEDULING,
    TimelineEventType.OBJECTION_RAISED: TimelineEventCategory.OBJECTION,
    TimelineEventType.AGREEMENT_REACHED: TimelineEventCategory.COMMITMENT,
    TimelineEventType.FOLLOW_UP_REQUESTED: TimelineEventCategory.COMMUNICATION,
    TimelineEventType.CONVERSATION_CLOSED: TimelineEventCategory.LIFECYCLE,
    TimelineEventType.CUSTOM_EVENT: TimelineEventCategory.CUSTOM,
}


class TimelineEventNormalizer:
    """Normalizes, validates timestamps, and deduplicates raw timeline events."""

    def normalize(self, events: List[TimelineEvent]) -> List[TimelineEvent]:
        """Performs full normalization pass over a list of extracted timeline events."""
        if not events:
            return []

        normalized: List[TimelineEvent] = []
        seen_signatures: Set[Tuple[str, str, str]] = set()

        for ev in events:
            # 1. Normalize timestamp (ensure UTC)
            ts = ev.occurred_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            # 2. Canonical category mapping
            expected_cat = EVENT_TYPE_TO_CATEGORY_MAP.get(ev.event_type, ev.category)

            # 3. Deduplication signature: (event_type, first_source_message_id_or_ts, title_snippet)
            source_msg = ""
            if ev.provenance and ev.provenance.source_message_ids:
                source_msg = ev.provenance.source_message_ids[0]
            else:
                source_msg = ts.isoformat()

            sig = (ev.event_type.value, source_msg, ev.title[:30].strip().lower())
            if sig in seen_signatures:
                logger.debug("Deduplicating duplicate timeline event: %s", sig)
                continue
            seen_signatures.add(sig)

            # 4. Canonicalize metadata & title
            clean_meta = {k: v for k, v in ev.metadata.items() if v is not None}
            clean_title = ev.title.strip()
            clean_desc = ev.description.strip()

            norm_ev = TimelineEvent(
                event_id=ev.event_id,
                conversation_id=ev.conversation_id,
                workspace_id=ev.workspace_id,
                event_type=ev.event_type,
                category=expected_cat,
                title=clean_title,
                description=clean_desc,
                occurred_at=ts,
                sequence_index=ev.sequence_index,
                time_offset_seconds=ev.time_offset_seconds,
                provenance=ev.provenance,
                confidence=max(0.0, min(1.0, ev.confidence)),
                metadata=clean_meta,
                created_at=ev.created_at,
            )
            normalized.append(norm_ev)

        return normalized


# Global default singleton instance
default_timeline_event_normalizer = TimelineEventNormalizer()
