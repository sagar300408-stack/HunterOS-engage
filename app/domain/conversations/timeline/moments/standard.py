"""
HunterOS Engage V1 - Standard Important Moment Rules
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic detection of high-value conversational moments.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.models import (
    ImportantMoment,
    ImportantMomentType,
    TimelineEventType,
)
from app.domain.conversations.timeline.moments.base import AbstractImportantMomentRule


class FirstRequirementMomentRule(AbstractImportantMomentRule):
    """Detects the initial customer requirement specification moment."""

    @property
    def rule_name(self) -> str:
        return "FirstRequirementMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.FIRST_REQUIREMENT

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        req_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.REQUIREMENT_IDENTIFIED
        ]
        if not req_events:
            return None

        first_req = req_events[0]
        msg_id = first_req.provenance.source_message_ids[0] if (first_req.provenance and first_req.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.FIRST_REQUIREMENT,
            title="First Requirement Stated",
            significance="Customer explicitly articulated initial property/service preferences.",
            timestamp=first_req.occurred_at,
            source_event_id=first_req.event_id,
            source_message_id=msg_id,
            snippet=first_req.description,
            confidence=first_req.confidence,
            metadata={"requirement_type": first_req.metadata.get("requirement_type")},
        )


class BudgetDiscussionMomentRule(AbstractImportantMomentRule):
    """Detects the moment financial capacity/budget is declared."""

    @property
    def rule_name(self) -> str:
        return "BudgetDiscussionMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.BUDGET_DISCUSSION

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        budget_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.BUDGET_MENTIONED
        ]
        if not budget_events:
            return None

        first_budget = budget_events[0]
        msg_id = first_budget.provenance.source_message_ids[0] if (first_budget.provenance and first_budget.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.BUDGET_DISCUSSION,
            title="Budget Declared",
            significance="Customer stated financial constraints and budget range.",
            timestamp=first_budget.occurred_at,
            source_event_id=first_budget.event_id,
            source_message_id=msg_id,
            snippet=first_budget.description,
            confidence=first_budget.confidence,
            metadata={"budget_value": first_budget.metadata.get("canonical_value") or first_budget.metadata.get("raw_value")},
        )


class FirstCommitmentMomentRule(AbstractImportantMomentRule):
    """Detects initial agreement or commitment."""

    @property
    def rule_name(self) -> str:
        return "FirstCommitmentMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.FIRST_COMMITMENT

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        agree_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.AGREEMENT_REACHED
        ]
        if not agree_events:
            return None

        first_agree = agree_events[0]
        msg_id = first_agree.provenance.source_message_ids[0] if (first_agree.provenance and first_agree.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.FIRST_COMMITMENT,
            title="Initial Commitment Made",
            significance="Customer confirmed interest and agreed to next steps.",
            timestamp=first_agree.occurred_at,
            source_event_id=first_agree.event_id,
            source_message_id=msg_id,
            snippet=first_agree.description,
            confidence=first_agree.confidence,
            metadata={},
        )


class FirstObjectionMomentRule(AbstractImportantMomentRule):
    """Detects the first objection or friction point."""

    @property
    def rule_name(self) -> str:
        return "FirstObjectionMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.FIRST_OBJECTION

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        obj_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.OBJECTION_RAISED
        ]
        if not obj_events:
            return None

        first_obj = obj_events[0]
        msg_id = first_obj.provenance.source_message_ids[0] if (first_obj.provenance and first_obj.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.FIRST_OBJECTION,
            title="Initial Objection Raised",
            significance="Customer voiced a pricing, timing, or feature concern.",
            timestamp=first_obj.occurred_at,
            source_event_id=first_obj.event_id,
            source_message_id=msg_id,
            snippet=first_obj.description,
            confidence=first_obj.confidence,
            metadata={},
        )


class DocumentExchangeMomentRule(AbstractImportantMomentRule):
    """Detects document or collateral exchange moment."""

    @property
    def rule_name(self) -> str:
        return "DocumentExchangeMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.DOCUMENT_EXCHANGE

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        doc_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.DOCUMENT_SHARED
        ]
        if not doc_events:
            return None

        first_doc = doc_events[0]
        msg_id = first_doc.provenance.source_message_ids[0] if (first_doc.provenance and first_doc.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.DOCUMENT_EXCHANGE,
            title="Collateral / Document Exchanged",
            significance="Official brochure, floor plan, or agreement shared.",
            timestamp=first_doc.occurred_at,
            source_event_id=first_doc.event_id,
            source_message_id=msg_id,
            snippet=first_doc.description,
            confidence=first_doc.confidence,
            metadata={"document": first_doc.metadata.get("document_name")},
        )


class MeetingConfirmationMomentRule(AbstractImportantMomentRule):
    """Detects appointment/meeting schedule confirmation."""

    @property
    def rule_name(self) -> str:
        return "MeetingConfirmationMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.MEETING_CONFIRMATION

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        meeting_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.MEETING_SCHEDULED
        ]
        if not meeting_events:
            return None

        first_meeting = meeting_events[0]
        msg_id = first_meeting.provenance.source_message_ids[0] if (first_meeting.provenance and first_meeting.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.MEETING_CONFIRMATION,
            title="Meeting Scheduled & Confirmed",
            significance="Live appointment or site visit committed in timeline.",
            timestamp=first_meeting.occurred_at,
            source_event_id=first_meeting.event_id,
            source_message_id=msg_id,
            snippet=first_meeting.description,
            confidence=first_meeting.confidence,
            metadata={},
        )


class CustomerDecisionMomentRule(AbstractImportantMomentRule):
    """Detects explicit customer decision statements."""

    @property
    def rule_name(self) -> str:
        return "CustomerDecisionMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.CUSTOMER_DECISION_STATEMENT

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        decision_events = [
            e for e in context.normalized_events
            if e.event_type in [TimelineEventType.AGREEMENT_REACHED, TimelineEventType.MEETING_SCHEDULED]
        ]
        if not decision_events:
            return None

        first_decision = decision_events[0]
        msg_id = first_decision.provenance.source_message_ids[0] if (first_decision.provenance and first_decision.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.CUSTOMER_DECISION_STATEMENT,
            title="Customer Decision Statement",
            significance="Customer explicitly declared a decision or agreement.",
            timestamp=first_decision.occurred_at,
            source_event_id=first_decision.event_id,
            source_message_id=msg_id,
            snippet=first_decision.description,
            confidence=first_decision.confidence,
            metadata={},
        )


class CustomMomentRule(AbstractImportantMomentRule):
    """Detects custom moments from custom events."""

    @property
    def rule_name(self) -> str:
        return "CustomMomentRule"

    @property
    def moment_type(self) -> ImportantMomentType:
        return ImportantMomentType.CUSTOM_IMPORTANT_MOMENT

    def evaluate(self, context: ConversationTimelineContext) -> Optional[ImportantMoment]:
        custom_events = [
            e for e in context.normalized_events
            if e.event_type == TimelineEventType.CUSTOM_EVENT
        ]
        if not custom_events:
            return None

        first_custom = custom_events[0]
        msg_id = first_custom.provenance.source_message_ids[0] if (first_custom.provenance and first_custom.provenance.source_message_ids) else None

        return ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.CUSTOM_IMPORTANT_MOMENT,
            title="Custom Significant Moment",
            significance="Custom business event flagged as significant moment.",
            timestamp=first_custom.occurred_at,
            source_event_id=first_custom.event_id,
            source_message_id=msg_id,
            snippet=first_custom.description,
            confidence=first_custom.confidence,
            metadata={"custom_key": first_custom.metadata.get("custom_key")},
        )
