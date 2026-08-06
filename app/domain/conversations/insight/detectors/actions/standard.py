"""
HunterOS Engage V1 - Standard Action Item Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Deterministic action item detectors generating explicit tasks originating
strictly from conversation evidence and timeline events.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.actions.base import AbstractActionItemDetector
from app.domain.conversations.insight.detectors.actions.registry import (
    ActionItemDetectorRegistry,
    default_action_item_detector_registry,
)
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    InsightCategory,
    InsightEvidence,
    InsightPriority,
)
from app.domain.conversations.timeline.models import TimelineEventType


class CustomerActionItemDetector(AbstractActionItemDetector):
    """Detects tasks and commitments assigned to or expected from the customer."""

    @property
    def detector_name(self) -> str:
        return "CustomerActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.CUSTOMER_ACTION}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        events = context.get_events()
        facts = context.get_facts()

        # Check for customer commitment events
        for e in events:
            if e.event_type == TimelineEventType.AGREEMENT_REACHED or (e.category.value == "COMMITMENT" and "customer" in e.title.lower()):
                actions.append(
                    ActionItemInsight(
                        category=InsightCategory.CUSTOMER_ACTION,
                        owner_type=ActionOwnerType.CUSTOMER,
                        title=f"Customer Commitment: {e.title}",
                        description=f"Customer confirmed commitment to proceed: '{e.description}'",
                        priority=InsightPriority.HIGH,
                        confidence=0.94,
                        evidence=InsightEvidence(
                            source_message_ids=e.provenance.source_message_ids if e.provenance else [],
                            source_event_ids=[e.event_id],
                            text_snippets=[e.description],
                            extraction_method="DETERMINISTIC_CUSTOMER_COMMITMENT_EVENT",
                        ),
                    )
                )

        # Check for customer date confirmation commitments in facts
        for f in facts:
            if f.category == FactCategory.DATE_REFERENCE:
                val_str = str(f.value).lower()
                if any(t in val_str for t in ("will confirm", "check with", "will let you know", "by saturday", "by sunday", "by tomorrow")):
                    actions.append(
                        ActionItemInsight(
                            category=InsightCategory.CUSTOMER_ACTION,
                            owner_type=ActionOwnerType.CUSTOMER,
                            title="Customer Confirmation Pending",
                            description=f"Customer stated they will confirm schedule/decision: '{f.value}'",
                            due_date_hint=str(f.value),
                            priority=InsightPriority.MEDIUM,
                            confidence=0.90,
                            evidence=InsightEvidence(
                                source_message_ids=f.source_message_ids,
                                fact_ids=[f.fact_id],
                                text_snippets=[str(f.value)],
                                extraction_method="DETERMINISTIC_CUSTOMER_DATE_COMMITMENT_FACT",
                            ),
                        )
                    )

        return actions


class InternalTeamActionItemDetector(AbstractActionItemDetector):
    """Detects obligations and promises made by the internal agent or team."""

    @property
    def detector_name(self) -> str:
        return "InternalTeamActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.INTERNAL_TEAM_ACTION}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        events = context.get_events()
        facts = context.get_facts()

        # Check for follow-up scheduled events
        for e in events:
            if e.event_type in (TimelineEventType.FOLLOW_UP_REQUESTED, TimelineEventType.CUSTOM_EVENT) or "follow" in e.title.lower():
                actions.append(
                    ActionItemInsight(
                        category=InsightCategory.INTERNAL_TEAM_ACTION,
                        owner_type=ActionOwnerType.INTERNAL_TEAM,
                        title=f"Execute Internal Follow-Up: {e.title}",
                        description=f"Internal team scheduled a follow-up action: '{e.description}'",
                        priority=InsightPriority.HIGH,
                        confidence=0.95,
                        evidence=InsightEvidence(
                            source_message_ids=e.provenance.source_message_ids if e.provenance else [],
                            source_event_ids=[e.event_id],
                            text_snippets=[e.description],
                            extraction_method="DETERMINISTIC_FOLLOWUP_EVENT_MAPPING",
                        ),
                    )
                )

        # Check for document sharing obligations
        doc_events = [e for e in events if e.event_type == TimelineEventType.DOCUMENT_SHARED or (e.category.value == "DOCUMENT" and "request" in e.title.lower())]
        for de in doc_events:
            actions.append(
                ActionItemInsight(
                    category=InsightCategory.INTERNAL_TEAM_ACTION,
                    owner_type=ActionOwnerType.INTERNAL_TEAM,
                    title=f"Dispatch Collateral: {de.title}",
                    description=f"Send requested documentation to customer: '{de.description}'",
                    priority=InsightPriority.HIGH,
                    confidence=0.93,
                    evidence=InsightEvidence(
                        source_message_ids=de.provenance.source_message_ids if de.provenance else [],
                        source_event_ids=[de.event_id],
                        text_snippets=[de.description],
                        extraction_method="DETERMINISTIC_DOC_DISPATCH_OBLIGATION",
                    ),
                )
            )

        return actions


class SharedActionItemDetector(AbstractActionItemDetector):
    """Detects joint activities such as scheduled visits, negotiations, or mutual calls."""

    @property
    def detector_name(self) -> str:
        return "SharedActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.SHARED_ACTION}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        events = context.get_events()
        milestones = context.get_milestones()

        meeting_events = [e for e in events if e.event_type == TimelineEventType.MEETING_SCHEDULED]
        for me in meeting_events:
            actions.append(
                ActionItemInsight(
                    category=InsightCategory.SHARED_ACTION,
                    owner_type=ActionOwnerType.SHARED,
                    title=f"Conduct Site Visit / Meeting: {me.title}",
                    description=f"Joint scheduled engagement between customer and team: '{me.description}'",
                    due_date_hint=me.occurred_at.isoformat() if me.occurred_at else None,
                    priority=InsightPriority.HIGH,
                    confidence=0.96,
                    evidence=InsightEvidence(
                        source_message_ids=me.provenance.source_message_ids,
                        source_event_ids=[me.event_id],
                        text_snippets=[me.description],
                        extraction_method="DETERMINISTIC_MEETING_EVENT_MAPPING",
                    ),
                )
            )

        return actions


class PendingResponseActionItemDetector(AbstractActionItemDetector):
    """Detects open queries awaiting customer or internal team response."""

    @property
    def detector_name(self) -> str:
        return "PendingResponseActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.PENDING_RESPONSE}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        events = context.get_events()
        question_events = [e for e in events if e.event_type == TimelineEventType.QUESTION_ASKED]

        for qe in question_events:
            actions.append(
                ActionItemInsight(
                    category=InsightCategory.PENDING_RESPONSE,
                    owner_type=ActionOwnerType.INTERNAL_TEAM,
                    title=f"Address Customer Question: {qe.title}",
                    description=f"Provide formal answer to customer query: '{qe.description}'",
                    priority=InsightPriority.MEDIUM,
                    confidence=0.91,
                    evidence=InsightEvidence(
                        source_message_ids=qe.provenance.source_message_ids,
                        source_event_ids=[qe.event_id],
                        text_snippets=[qe.description],
                        extraction_method="DETERMINISTIC_OPEN_QUERY_ACTION",
                    ),
                )
            )

        return actions


class RequestedDocumentActionItemDetector(AbstractActionItemDetector):
    """Detects specific collateral items requested during the conversation."""

    @property
    def detector_name(self) -> str:
        return "RequestedDocumentActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.REQUESTED_DOCUMENT}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        facts = context.get_facts()
        doc_facts = [f for f in facts if f.category == FactCategory.DOCUMENT_MENTIONED]

        for df in doc_facts:
            actions.append(
                ActionItemInsight(
                    category=InsightCategory.REQUESTED_DOCUMENT,
                    owner_type=ActionOwnerType.INTERNAL_TEAM,
                    title=f"Prepare Requested Material: {df.value}",
                    description=f"Prepare and dispatch documented artifact: '{df.value}'",
                    priority=InsightPriority.HIGH,
                    confidence=0.92,
                    evidence=InsightEvidence(
                        source_message_ids=df.source_message_ids,
                        fact_ids=[df.fact_id],
                        text_snippets=[str(df.value)],
                        extraction_method="DETERMINISTIC_FACT_DOCUMENT_ACTION",
                    ),
                )
            )

        return actions


class ScheduledActivityActionItemDetector(AbstractActionItemDetector):
    """Detects calendar appointments, site walkthroughs, and inspection slots."""

    @property
    def detector_name(self) -> str:
        return "ScheduledActivityActionItemDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.SCHEDULED_ACTIVITY}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        actions: List[ActionItemInsight] = []
        facts = context.get_facts()
        date_facts = [f for f in facts if f.category == FactCategory.DATE_REFERENCE]

        for df in date_facts:
            actions.append(
                ActionItemInsight(
                    category=InsightCategory.SCHEDULED_ACTIVITY,
                    owner_type=ActionOwnerType.SHARED,
                    title=f"Execute Scheduled Calendar Item ({df.value})",
                    description=f"Calendar engagement identified from conversation date facts: '{df.value}'",
                    due_date_hint=str(df.value),
                    priority=InsightPriority.HIGH,
                    confidence=0.93,
                    evidence=InsightEvidence(
                        source_message_ids=df.source_message_ids,
                        fact_ids=[df.fact_id],
                        text_snippets=[str(df.value)],
                        extraction_method="DETERMINISTIC_DATE_FACT_CALENDAR_ACTION",
                    ),
                )
            )

        return actions


class CustomActionItemDetector(AbstractActionItemDetector):
    """Configurable detector allowing dynamic registration of custom action item rules."""

    def __init__(
        self,
        name: str,
        category: InsightCategory = InsightCategory.CUSTOM_ACTION,
        eval_fn: Optional[Callable[[ConversationInsightContext], List[ActionItemInsight]]] = None,
    ) -> None:
        self._name = name
        self._category = category
        self._eval_fn = eval_fn

    @property
    def detector_name(self) -> str:
        return self._name

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {self._category}

    def detect(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        if self._eval_fn:
            return self._eval_fn(context)
        return []


def register_standard_action_item_detectors(registry: ActionItemDetectorRegistry) -> None:
    """Registers all 6 standard action item detectors into the registry."""
    registry.register(CustomerActionItemDetector())
    registry.register(InternalTeamActionItemDetector())
    registry.register(SharedActionItemDetector())
    registry.register(PendingResponseActionItemDetector())
    registry.register(RequestedDocumentActionItemDetector())
    registry.register(ScheduledActivityActionItemDetector())


# Populate default singleton registry
register_standard_action_item_detectors(default_action_item_detector_registry)
