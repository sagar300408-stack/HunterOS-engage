"""
HunterOS Engage V1 - Standard Milestone Rules
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic evaluation rules for conversational business milestones.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.milestones.base import AbstractMilestoneRule
from app.domain.conversations.timeline.models import (
    MilestoneType,
    TimelineEvent,
    TimelineEventType,
    TimelineMilestone,
)


class InitialEngagementRule(AbstractMilestoneRule):
    """Detects initial conversational engagement milestone."""

    @property
    def rule_name(self) -> str:
        return "InitialEngagementRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.INITIAL_ENGAGEMENT

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        matching_events = [
            e for e in context.normalized_events
            if e.event_type in [TimelineEventType.CONVERSATION_STARTED, TimelineEventType.CUSTOMER_INTRODUCED]
        ]
        if not matching_events:
            return None

        earliest = matching_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.INITIAL_ENGAGEMENT,
            title="Initial Engagement Established",
            description=f"Initial contact established with customer across {len(matching_events)} interaction events.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in matching_events],
            confidence=1.0,
            metadata={"events_count": len(matching_events)},
        )


class NeedsAlignedRule(AbstractMilestoneRule):
    """Detects customer needs / requirements identification milestone."""

    @property
    def rule_name(self) -> str:
        return "NeedsAlignedRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.NEEDS_ALIGNED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        req_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.REQUIREMENT_IDENTIFIED
        ]
        if not req_events:
            return None

        earliest = req_events[0]
        specs = [e.metadata.get("raw_value") for e in req_events if e.metadata.get("raw_value")]
        spec_summary = ", ".join(specs[:3]) if specs else "key requirements"

        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.NEEDS_ALIGNED,
            title="Customer Requirements Aligned",
            description=f"Customer requirements and preferences captured: {spec_summary}.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in req_events],
            confidence=0.95,
            metadata={"requirements_count": len(req_events), "specs": specs},
        )


class BudgetEstablishedRule(AbstractMilestoneRule):
    """Detects budget clarity milestone."""

    @property
    def rule_name(self) -> str:
        return "BudgetEstablishedRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.BUDGET_ESTABLISHED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        budget_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.BUDGET_MENTIONED
        ]
        if not budget_events:
            return None

        earliest = budget_events[0]
        val = earliest.metadata.get("canonical_value") or earliest.metadata.get("raw_value") or "stated"

        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.BUDGET_ESTABLISHED,
            title="Budget Parameters Established",
            description=f"Financial budget established: {val}.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in budget_events],
            confidence=0.98,
            metadata={"budget_events_count": len(budget_events), "budget_value": val},
        )


class CommercialTermsRule(AbstractMilestoneRule):
    """Detects commercial terms & document sharing milestone."""

    @property
    def rule_name(self) -> str:
        return "CommercialTermsRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.COMMERCIAL_TERMS_DISCUSSED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        commercial_events = [
            e for e in context.normalized_events
            if e.event_type in [TimelineEventType.DOCUMENT_SHARED, TimelineEventType.INFORMATION_SHARED]
        ]
        if len(commercial_events) < 1:
            return None

        earliest = commercial_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.COMMERCIAL_TERMS_DISCUSSED,
            title="Commercial & Technical Information Exchanged",
            description=f"Exchanged collateral and technical details ({len(commercial_events)} items).",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in commercial_events],
            confidence=0.90,
            metadata={"items_count": len(commercial_events)},
        )


class AppointmentCommittedRule(AbstractMilestoneRule):
    """Detects meeting / site visit commitment milestone."""

    @property
    def rule_name(self) -> str:
        return "AppointmentCommittedRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.APPOINTMENT_COMMITTED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        meeting_events = [
            e for e in context.normalized_events
            if e.event_type in [TimelineEventType.MEETING_SCHEDULED, TimelineEventType.MEETING_COMPLETED]
        ]
        if not meeting_events:
            return None

        earliest = meeting_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.APPOINTMENT_COMMITTED,
            title="Appointment / Site Visit Committed",
            description="Appointment, demo, or site visit committed in conversation.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in meeting_events],
            confidence=0.92,
            metadata={"events_count": len(meeting_events)},
        )


class CommitmentFinalizedRule(AbstractMilestoneRule):
    """Detects agreement reached milestone."""

    @property
    def rule_name(self) -> str:
        return "CommitmentFinalizedRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.COMMITMENT_FINALIZED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        agreement_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.AGREEMENT_REACHED
        ]
        if not agreement_events:
            return None

        earliest = agreement_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.COMMITMENT_FINALIZED,
            title="Commitment Finalized",
            description="Mutual agreement and commitment reached.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in agreement_events],
            confidence=0.90,
            metadata={"agreements_count": len(agreement_events)},
        )


class SessionConcludedRule(AbstractMilestoneRule):
    """Detects conversation closed milestone."""

    @property
    def rule_name(self) -> str:
        return "SessionConcludedRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.SESSION_CONCLUDED

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        close_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.CONVERSATION_CLOSED
        ]
        if not close_events:
            return None

        close_ev = close_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.SESSION_CONCLUDED,
            title="Conversation Session Concluded",
            description="Conversation session formally concluded.",
            timestamp=close_ev.occurred_at,
            source_event_ids=[close_ev.event_id],
            confidence=1.0,
            metadata={},
        )


class CustomMilestoneRule(AbstractMilestoneRule):
    """Evaluates custom milestones from custom events."""

    @property
    def rule_name(self) -> str:
        return "CustomMilestoneRule"

    @property
    def milestone_type(self) -> MilestoneType:
        return MilestoneType.CUSTOM_MILESTONE

    def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
        custom_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.CUSTOM_EVENT
        ]
        if not custom_events:
            return None

        earliest = custom_events[0]
        return TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.CUSTOM_MILESTONE,
            title="Custom Milestone Reached",
            description=f"Custom milestone achieved with {len(custom_events)} custom events.",
            timestamp=earliest.occurred_at,
            source_event_ids=[e.event_id for e in custom_events],
            confidence=0.85,
            metadata={"custom_events_count": len(custom_events)},
        )
