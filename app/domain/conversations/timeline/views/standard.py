"""
HunterOS Engage V1 - Standard Timeline Projection Views
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic timeline views for executives, audit logs, and downstream intelligence modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.conversations.timeline.models import (
    ConversationTimeline,
    TimelineViewFormat,
)
from app.domain.conversations.timeline.views.base import AbstractTimelineView


class ChronologicalEventView(AbstractTimelineView):
    """Full chronological event view with detailed provenance and offsets."""

    @property
    def view_name(self) -> str:
        return "chronological_events"

    @property
    def view_format(self) -> TimelineViewFormat:
        return TimelineViewFormat.CHRONOLOGICAL_EVENTS

    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        stream = timeline.event_stream
        events_list: List[Dict[str, Any]] = []

        if stream and stream.events:
            for ev in stream.events:
                events_list.append({
                    "sequence_index": ev.sequence_index,
                    "event_id": str(ev.event_id),
                    "event_type": ev.event_type.value,
                    "category": ev.category.value,
                    "title": ev.title,
                    "description": ev.description,
                    "occurred_at": ev.occurred_at.isoformat(),
                    "time_offset_seconds": ev.time_offset_seconds,
                    "confidence": ev.confidence,
                    "metadata": ev.metadata,
                    "provenance": {
                        "analysis_id": str(ev.provenance.analysis_id) if ev.provenance and ev.provenance.analysis_id else None,
                        "fact_id": str(ev.provenance.fact_id) if ev.provenance and ev.provenance.fact_id else None,
                        "source_message_ids": ev.provenance.source_message_ids if ev.provenance else [],
                        "pipeline_stage": ev.provenance.pipeline_stage if ev.provenance else None,
                    } if ev.provenance else None,
                })

        return {
            "view": self.view_name,
            "conversation_id": timeline.conversation_id,
            "workspace_id": str(timeline.workspace_id) if timeline.workspace_id else None,
            "total_events": len(events_list),
            "events": events_list,
        }


class MilestoneOnlyView(AbstractTimelineView):
    """Business milestone summary view."""

    @property
    def view_name(self) -> str:
        return "milestones_only"

    @property
    def view_format(self) -> TimelineViewFormat:
        return TimelineViewFormat.MILESTONES_ONLY

    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        milestones_list: List[Dict[str, Any]] = []

        for ms in timeline.milestones:
            milestones_list.append({
                "milestone_id": str(ms.milestone_id),
                "milestone_type": ms.milestone_type.value,
                "title": ms.title,
                "description": ms.description,
                "timestamp": ms.timestamp.isoformat(),
                "confidence": ms.confidence,
                "source_event_ids": [str(eid) for eid in ms.source_event_ids],
                "metadata": ms.metadata,
            })

        return {
            "view": self.view_name,
            "conversation_id": timeline.conversation_id,
            "total_milestones": len(milestones_list),
            "milestones": milestones_list,
        }


class ImportantMomentsView(AbstractTimelineView):
    """Critical decision, objection, and alignment moments view."""

    @property
    def view_name(self) -> str:
        return "important_moments"

    @property
    def view_format(self) -> TimelineViewFormat:
        return TimelineViewFormat.IMPORTANT_MOMENTS

    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        moments_list: List[Dict[str, Any]] = []

        for mom in timeline.important_moments:
            moments_list.append({
                "moment_id": str(mom.moment_id),
                "moment_type": mom.moment_type.value,
                "title": mom.title,
                "significance": mom.significance,
                "timestamp": mom.timestamp.isoformat(),
                "snippet": mom.snippet,
                "confidence": mom.confidence,
                "source_event_id": str(mom.source_event_id) if mom.source_event_id else None,
                "source_message_id": mom.source_message_id,
                "metadata": mom.metadata,
            })

        return {
            "view": self.view_name,
            "conversation_id": timeline.conversation_id,
            "total_moments": len(moments_list),
            "important_moments": moments_list,
        }


class ExecutiveSummaryTimelineView(AbstractTimelineView):
    """High-level executive briefing view."""

    @property
    def view_name(self) -> str:
        return "executive_summary"

    @property
    def view_format(self) -> TimelineViewFormat:
        return TimelineViewFormat.EXECUTIVE_SUMMARY

    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        meta = timeline.metadata

        key_milestones = [
            {"milestone": ms.title, "timestamp": ms.timestamp.isoformat()}
            for ms in timeline.milestones
        ]
        key_moments = [
            {"moment": mom.title, "significance": mom.significance, "snippet": mom.snippet}
            for mom in timeline.important_moments
        ]

        return {
            "view": self.view_name,
            "conversation_id": timeline.conversation_id,
            "workspace_id": str(timeline.workspace_id) if timeline.workspace_id else None,
            "customer_id": timeline.customer_id,
            "duration_seconds": meta.duration_seconds if meta else 0.0,
            "total_events": meta.total_events if meta else 0,
            "event_breakdown": meta.event_category_distribution if meta else {},
            "key_milestones": key_milestones,
            "key_moments": key_moments,
            "timeline_version": timeline.timeline_version,
            "is_valid": timeline.diagnostics.is_valid if timeline.diagnostics else True,
        }


class ParticipantSpecificView(AbstractTimelineView):
    """Filters timeline events for a specific sender or party."""

    @property
    def view_name(self) -> str:
        return "participant_timeline"

    @property
    def view_format(self) -> TimelineViewFormat:
        return TimelineViewFormat.PARTICIPANT_TIMELINE

    def render(self, timeline: ConversationTimeline, **kwargs: Any) -> Dict[str, Any]:
        target_sender = kwargs.get("sender_type", "customer")
        stream = timeline.event_stream
        filtered_events: List[Dict[str, Any]] = []

        if stream and stream.events:
            for ev in stream.events:
                # Check metadata for sender type
                sender = ev.metadata.get("sender_type") or ev.metadata.get("sender")
                if not sender or str(sender).lower() == str(target_sender).lower():
                    filtered_events.append({
                        "sequence_index": ev.sequence_index,
                        "event_type": ev.event_type.value,
                        "title": ev.title,
                        "description": ev.description,
                        "occurred_at": ev.occurred_at.isoformat(),
                        "time_offset_seconds": ev.time_offset_seconds,
                    })

        return {
            "view": self.view_name,
            "participant": target_sender,
            "conversation_id": timeline.conversation_id,
            "events_count": len(filtered_events),
            "events": filtered_events,
        }
