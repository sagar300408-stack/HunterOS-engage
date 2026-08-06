"""
HunterOS Engage V1 - Timeline Validation Framework
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Strict architectural invariants, chronological consistency, reference integrity,
and boundary validation for conversation timelines.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Set

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import (
    ConversationTimeline,
    TimelineEvent,
)

logger = logging.getLogger(__name__)

FORBIDDEN_KEYS: Set[str] = {
    "intent",
    "predicted_intent",
    "intent_score",
    "sentiment",
    "sentiment_score",
    "sentiment_label",
    "recommendation",
    "recommended_action",
    "lead_score",
    "journey_stage_update",
    "autonomous_decision",
}


class TimelineValidationError(Exception):
    """Raised when timeline validation detects fatal invariant breach."""
    pass


class TimelineValidationFramework:
    """Validates structural integrity, chronological consistency, lineage, and architectural boundaries."""

    def validate(self, context: ConversationTimelineContext, raise_on_error: bool = False) -> List[str]:
        """Runs full validation suite against the timeline execution context."""
        errors: List[str] = []

        # 1. Chronological Ordering Validation
        events = context.normalized_events
        for i in range(len(events) - 1):
            curr = events[i]
            nxt = events[i + 1]
            if curr.occurred_at > nxt.occurred_at:
                errors.append(
                    f"Chronological inversion at index {i} -> {i+1}: "
                    f"Event {curr.event_type.value} ({curr.occurred_at.isoformat()}) occurs after "
                    f"Event {nxt.event_type.value} ({nxt.occurred_at.isoformat()})"
                )

        # 2. Sequence indices and relative offsets
        for i, ev in enumerate(events):
            if ev.sequence_index != i:
                errors.append(f"Invalid sequence index at position {i}: found {ev.sequence_index}")
            if ev.time_offset_seconds < 0.0:
                errors.append(f"Negative time offset at event {ev.event_id}: {ev.time_offset_seconds}s")

            # Timezone awareness
            if ev.occurred_at.tzinfo is None:
                errors.append(f"Timezone-naive timestamp detected at event {ev.event_id}")

            # Confidence bounds
            if not (0.0 <= ev.confidence <= 1.0):
                errors.append(f"Confidence score out of bounds [0.0, 1.0] at event {ev.event_id}: {ev.confidence}")

        # 3. Source Message Reference Integrity
        if context.analysis_result:
            valid_msg_ids = set()
            if hasattr(context.analysis_result, "normalized_messages") and context.analysis_result.normalized_messages:
                for m in context.analysis_result.normalized_messages:
                    mid = getattr(m, "id", None) or getattr(m, "message_id", None)
                    if mid:
                        valid_msg_ids.add(mid)
            if context.analysis_result.facts:
                for f in context.analysis_result.facts:
                    if f.provenance and f.provenance.source_messages:
                        for ref in f.provenance.source_messages:
                            if ref.message_id:
                                valid_msg_ids.add(ref.message_id)
            if context.analysis_result.segments:
                for s in context.analysis_result.segments:
                    if s.start_message_id:
                        valid_msg_ids.add(s.start_message_id)
                    if s.end_message_id:
                        valid_msg_ids.add(s.end_message_id)
            if context.analysis_result.topics and getattr(context.analysis_result.topics, "timeline", None):
                for t in context.analysis_result.topics.timeline:
                    if t.message_id:
                        valid_msg_ids.add(t.message_id)
            valid_msg_ids.add("msg_start")
            valid_msg_ids.add("msg_end")

            if valid_msg_ids:
                for ev in events:
                    if ev.provenance and ev.provenance.source_message_ids:
                        for mid in ev.provenance.source_message_ids:
                            if mid and mid not in valid_msg_ids:
                                errors.append(f"Broken message reference in event {ev.event_id}: message_id '{mid}' not found in analysis result")

        # 4. Cross-workspace isolation
        if context.workspace_id:
            for ev in events:
                if ev.workspace_id and ev.workspace_id != context.workspace_id:
                    errors.append(f"Cross-workspace contamination at event {ev.event_id}: event workspace {ev.workspace_id} != context workspace {context.workspace_id}")

        # 5. Boundary & Forbidden Key Guard
        for ev in events:
            self._check_forbidden_keys(ev.metadata, f"event {ev.event_id}", errors)
        for ms in context.milestones:
            self._check_forbidden_keys(ms.metadata, f"milestone {ms.milestone_id}", errors)
            if not (0.0 <= ms.confidence <= 1.0):
                errors.append(f"Confidence out of bounds in milestone {ms.milestone_id}: {ms.confidence}")
        for mom in context.important_moments:
            self._check_forbidden_keys(mom.metadata, f"moment {mom.moment_id}", errors)
            if not (0.0 <= mom.confidence <= 1.0):
                errors.append(f"Confidence out of bounds in moment {mom.moment_id}: {mom.confidence}")

        # Log & attach errors
        for err in errors:
            context.add_validation_error(err)
            logger.error("Timeline validation failure: %s", err)

        if errors and raise_on_error:
            raise TimelineValidationError(f"Timeline validation failed with {len(errors)} errors: {errors[0]}")

        return errors

    def _check_forbidden_keys(self, data: dict, label: str, errors: List[str]) -> None:
        """Recursively checks for forbidden predictive or mutating keys."""
        for k, v in data.items():
            if k.lower() in FORBIDDEN_KEYS:
                errors.append(f"Architectural boundary breach: forbidden key '{k}' found in {label}")
            if isinstance(v, dict):
                self._check_forbidden_keys(v, label, errors)


# Global default singleton instance
default_timeline_validation_framework = TimelineValidationFramework()
