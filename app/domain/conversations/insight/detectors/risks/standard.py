"""
HunterOS Engage V1 - Standard Risk Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Deterministic, descriptive risk detectors evaluating Conversation Analysis
and Conversation Timeline artifacts with complete lineage evidence.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.risks.base import AbstractRiskDetector
from app.domain.conversations.insight.detectors.risks.registry import (
    RiskDetectorRegistry,
    default_risk_detector_registry,
)
from app.domain.conversations.insight.models import (
    InsightCategory,
    InsightEvidence,
    InsightPriority,
    RiskInsight,
)
from app.domain.conversations.timeline.models import TimelineEventType


class MissingInformationRiskDetector(AbstractRiskDetector):
    """Detects missing essential customer or project qualification data."""

    @property
    def detector_name(self) -> str:
        return "MissingInformationRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.MISSING_INFORMATION}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        facts = context.get_facts()
        segments = context.get_segments()
        events = context.get_events()

        has_contact_fact = any(f.category == FactCategory.CONTACT_INFO for f in facts)
        has_budget_fact = any(f.category == FactCategory.BUDGET_REFERENCE for f in facts)
        has_requirement_fact = any(f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE) for f in facts)

        # If requirements exist but budget is completely missing
        if has_requirement_fact and not has_budget_fact:
            source_msgs: List[str] = []
            fact_ids: List[uuid.UUID] = []
            for f in facts:
                if f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE):
                    source_msgs.extend(f.source_message_ids)
                    fact_ids.append(f.fact_id)

            risks.append(
                RiskInsight(
                    category=InsightCategory.MISSING_INFORMATION,
                    title="Missing Customer Budget Specification",
                    description="Requirements have been specified by the customer, but no budget has been captured.",
                    impact_description="May result in misaligned proposals or unqualified pipeline tracking.",
                    priority=InsightPriority.HIGH,
                    confidence=0.95,
                    evidence=InsightEvidence(
                        source_message_ids=list(dict.fromkeys(source_msgs)),
                        fact_ids=fact_ids,
                        extraction_method="DETERMINISTIC_FACT_GAP_ANALYSIS",
                    ),
                )
            )

        # If conversation has multiple segments but no contact details
        if len(segments) >= 2 and not has_contact_fact and not context.customer_id:
            first_seg = segments[0]
            risks.append(
                RiskInsight(
                    category=InsightCategory.MISSING_INFORMATION,
                    title="Missing Verified Customer Contact Details",
                    description="Customer engaged across multiple conversation segments without verified phone or email on record.",
                    impact_description="Inability to execute direct follow-ups outside current channel.",
                    priority=InsightPriority.MEDIUM,
                    confidence=0.90,
                    evidence=InsightEvidence(
                        source_message_ids=first_seg.message_ids[:2] if first_seg.message_ids else [],
                        extraction_method="DETERMINISTIC_METADATA_GAP_ANALYSIS",
                    ),
                )
            )

        return risks


class UnansweredQuestionRiskDetector(AbstractRiskDetector):
    """Detects unanswered customer questions or unaddressed inquiries."""

    @property
    def detector_name(self) -> str:
        return "UnansweredQuestionRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.UNANSWERED_QUESTION}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        events = context.get_events()
        segments = context.get_segments()

        # Check for QUESTION events without subsequent answer or closing
        question_events = [e for e in events if e.event_type == TimelineEventType.QUESTION_ASKED]
        info_events = [
            e for e in events
            if e.event_type in (
                TimelineEventType.INFORMATION_SHARED,
                TimelineEventType.DOCUMENT_SHARED,
                TimelineEventType.MEETING_SCHEDULED,
            )
        ]

        for q_ev in question_events:
            # Check if there is an info event occurring AFTER this question
            answered = any(ie.sequence_index > q_ev.sequence_index for ie in info_events)
            if not answered:
                risks.append(
                    RiskInsight(
                        category=InsightCategory.UNANSWERED_QUESTION,
                        title=f"Unresolved Customer Question: {q_ev.title}",
                        description=f"A customer inquiry was logged ('{q_ev.title}') but no subsequent informative response was recorded in the timeline.",
                        impact_description="Customer inquiry remains pending resolution, impacting engagement satisfaction.",
                        priority=InsightPriority.HIGH,
                        confidence=0.92,
                        evidence=InsightEvidence(
                            source_message_ids=q_ev.provenance.source_message_ids,
                            source_event_ids=[q_ev.event_id],
                            text_snippets=[q_ev.description],
                            extraction_method="DETERMINISTIC_EVENT_STREAM_PAIRING",
                        ),
                    )
                )

        # Fallback check across segments
        if not question_events:
            for seg in segments:
                if seg.summary and "?" in seg.summary and seg.segment_index == len(segments) - 1:
                    risks.append(
                        RiskInsight(
                            category=InsightCategory.UNANSWERED_QUESTION,
                            title="Open Question in Final Segment",
                            description=f"Final conversation segment ends with an unresolved query: '{seg.summary}'",
                            impact_description="Customer waiting for team response.",
                            priority=InsightPriority.MEDIUM,
                            confidence=0.85,
                            evidence=InsightEvidence(
                                source_message_ids=seg.message_ids,
                                text_snippets=[seg.summary],
                                extraction_method="DETERMINISTIC_SEGMENT_INSPECTION",
                            ),
                        )
                    )

        return risks


class MissingDocumentRiskDetector(AbstractRiskDetector):
    """Detects requested documents or brochures that have not been dispatched."""

    @property
    def detector_name(self) -> str:
        return "MissingDocumentRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.MISSING_DOCUMENT}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        events = context.get_events()
        facts = context.get_facts()

        doc_req_events = [
            e for e in events
            if e.event_type == TimelineEventType.DOCUMENT_REQUESTED
            or (e.category.value == "DOCUMENT" and "request" in e.title.lower())
        ]
        doc_shared_events = [
            e for e in events
            if e.event_type == TimelineEventType.DOCUMENT_SHARED
            or (e.category.value == "DOCUMENT" and "share" in e.title.lower())
        ]

        for req_ev in doc_req_events:
            fulfilled = any(se.sequence_index > req_ev.sequence_index for se in doc_shared_events)
            if not fulfilled:
                risks.append(
                    RiskInsight(
                        category=InsightCategory.MISSING_DOCUMENT,
                        title=f"Unfulfilled Document Request: {req_ev.title}",
                        description=f"Customer requested collateral/documentation ('{req_ev.title}') which has not yet been shared.",
                        impact_description="Collateral delivery delayed, stalling buyer evaluation.",
                        priority=InsightPriority.HIGH,
                        confidence=0.94,
                        evidence=InsightEvidence(
                            source_message_ids=req_ev.provenance.source_message_ids,
                            source_event_ids=[req_ev.event_id],
                            text_snippets=[req_ev.description],
                            extraction_method="DETERMINISTIC_EVENT_STREAM_PAIRING",
                        ),
                    )
                )

        # Also check facts for document requests
        doc_facts = [f for f in facts if f.category == FactCategory.DOCUMENT and "request" in str(f.value).lower()]
        for df in doc_facts:
            if not doc_shared_events and not any(r.evidence.fact_ids == [df.fact_id] for r in risks):
                risks.append(
                    RiskInsight(
                        category=InsightCategory.MISSING_DOCUMENT,
                        title="Document Requested But Not Sent",
                        description=f"Document requested in conversation facts: {df.value}",
                        impact_description="Pending collateral dispatch.",
                        priority=InsightPriority.MEDIUM,
                        confidence=0.88,
                        evidence=InsightEvidence(
                            source_message_ids=df.source_message_ids,
                            fact_ids=[df.fact_id],
                            text_snippets=[str(df.value)],
                            extraction_method="DETERMINISTIC_FACT_DOCUMENT_INSPECTION",
                        ),
                    )
                )

        return risks


class DelayedResponseRiskDetector(AbstractRiskDetector):
    """Detects response delays or prolonged inactivity periods."""

    @property
    def detector_name(self) -> str:
        return "DelayedResponseRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.DELAYED_RESPONSE}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        events = context.get_events()

        # Check consecutive events for significant gaps (> 24 hours)
        for i in range(len(events) - 1):
            curr_ev = events[i]
            next_ev = events[i + 1]
            if curr_ev.occurred_at and next_ev.occurred_at:
                delta_s = (next_ev.occurred_at - curr_ev.occurred_at).total_seconds()
                if delta_s > 86400:  # > 24 hours
                    hours = round(delta_s / 3600, 1)
                    curr_msgs = curr_ev.provenance.source_message_ids if curr_ev.provenance else []
                    next_msgs = next_ev.provenance.source_message_ids if next_ev.provenance else []
                    risks.append(
                        RiskInsight(
                            category=InsightCategory.DELAYED_RESPONSE,
                            title=f"Prolonged Turnaround Gap ({hours}h)",
                            description=f"A gap of {hours} hours elapsed between event '{curr_ev.title}' and '{next_ev.title}'.",
                            impact_description="Customer engagement momentum stalled due to response latency.",
                            priority=InsightPriority.MEDIUM if hours < 48 else InsightPriority.HIGH,
                            confidence=0.98,
                            evidence=InsightEvidence(
                                source_message_ids=curr_msgs + next_msgs,
                                source_event_ids=[curr_ev.event_id, next_ev.event_id],
                                text_snippets=[f"Gap: {hours} hours"],
                                extraction_method="DETERMINISTIC_TIMESTAMP_DELTA_ANALYSIS",
                            ),
                        )
                    )

        # Check for long duration single segments or stalled conversations
        if context.metadata and context.metadata.duration_seconds > 1800:
            if context.metadata.message_count < 4:
                risks.append(
                    RiskInsight(
                        category=InsightCategory.DELAYED_RESPONSE,
                        title="High Latency / Extended Inactivity Observed",
                        description=f"Conversation spans {context.metadata.duration_seconds / 60:.1f} minutes with only {context.metadata.message_count} messages exchanged.",
                        impact_description="Customer engagement momentum stalled due to response latency.",
                        priority=InsightPriority.LOW,
                        confidence=0.85,
                        evidence=InsightEvidence(
                            source_message_ids=[],
                            text_snippets=[f"Duration: {context.metadata.duration_seconds}s, Count: {context.metadata.message_count}"],
                            extraction_method="DETERMINISTIC_TEMPORAL_RATIO_ANALYSIS",
                        ),
                    )
                )

        return risks


class BudgetGapRiskDetector(AbstractRiskDetector):
    """Detects budget mismatches, financial friction, or pricing objections."""

    @property
    def detector_name(self) -> str:
        return "BudgetGapRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.BUDGET_GAP}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        facts = context.get_facts()
        events = context.get_events()

        budget_facts = [f for f in facts if f.category == FactCategory.BUDGET_REFERENCE]
        objection_events = [
            e for e in events
            if e.event_type == TimelineEventType.OBJECTION_RAISED
            and "budget" in (e.title + e.description).lower()
        ]

        for ob in objection_events:
            risks.append(
                RiskInsight(
                    category=InsightCategory.BUDGET_GAP,
                    title=f"Budget Objection Identified: {ob.title}",
                    description=f"A budget or pricing objection was recorded: '{ob.description}'",
                    impact_description="Deal at risk due to pricing or financial mismatch.",
                    priority=InsightPriority.HIGH,
                    confidence=0.95,
                    evidence=InsightEvidence(
                        source_message_ids=ob.provenance.source_message_ids if ob.provenance else [],
                        source_event_ids=[ob.event_id],
                        text_snippets=[ob.description],
                        extraction_method="DETERMINISTIC_OBJECTION_EVENT_MAPPING",
                    ),
                )
            )

        for bf in budget_facts:
            val_str = str(bf.value).lower()
            if any(term in val_str for term in ("tight", "strict", "limit", "max", "stretch", "low", "concern", "high")):
                risks.append(
                    RiskInsight(
                        category=InsightCategory.BUDGET_GAP,
                        title="Strict Budget Ceiling Recorded",
                        description=f"Customer indicated strict financial bounds: '{bf.value}'",
                        impact_description="Potential ceiling constraint for premium unit allocation.",
                        priority=InsightPriority.HIGH,
                        confidence=0.90,
                        evidence=InsightEvidence(
                            source_message_ids=bf.source_message_ids,
                            fact_ids=[bf.fact_id],
                            text_snippets=[str(bf.value)],
                            extraction_method="DETERMINISTIC_FACT_PATTERN_MATCH",
                        ),
                    )
                )

        return risks


class TimelineConflictRiskDetector(AbstractRiskDetector):
    """Detects conflicting schedules, urgent deadlines, or scheduling frictions."""

    @property
    def detector_name(self) -> str:
        return "TimelineConflictRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.TIMELINE_CONFLICT}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        facts = context.get_facts()
        date_facts = [f for f in facts if f.category == FactCategory.DATE_REFERENCE]

        # Check for urgent move-in or strict deadline markers
        for df in date_facts:
            val_str = str(df.value).lower()
            if any(k in val_str for k in ("immediate", "urgent", "asap", "within a week", "conflict", "reschedule", "delay")):
                risks.append(
                    RiskInsight(
                        category=InsightCategory.TIMELINE_CONFLICT,
                        title="Urgent Timeline Constraint / Scheduling Pressure",
                        description=f"Customer date constraint requires expedited turnaround: '{df.value}'",
                        impact_description="Operational pressure to accelerate possession or viewing availability.",
                        priority=InsightPriority.HIGH,
                        confidence=0.90,
                        evidence=InsightEvidence(
                            source_message_ids=df.source_message_ids,
                            fact_ids=[df.fact_id],
                            text_snippets=[str(df.value)],
                            extraction_method="DETERMINISTIC_DATE_FACT_ANALYSIS",
                        ),
                    )
                )

        return risks


class RequirementAmbiguityRiskDetector(AbstractRiskDetector):
    """Detects conflicting or underspecified customer requirements."""

    @property
    def detector_name(self) -> str:
        return "RequirementAmbiguityRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.REQUIREMENT_AMBIGUITY}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        facts = context.get_facts()
        req_facts = [f for f in facts if f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE)]

        # Check for multiple differing configurations (e.g., both 2BHK and 4BHK) or ambiguity keywords
        unit_types = set()
        for rf in req_facts:
            match = re.findall(r"\b(\d\s*bhk|\d\s*bedroom)\b", str(rf.value), re.IGNORECASE)
            for m in match:
                unit_types.add(m.lower().replace(" ", ""))

        if len(unit_types) > 1:
            all_msgs: List[str] = []
            f_ids: List[uuid.UUID] = []
            for rf in req_facts:
                all_msgs.extend(rf.source_message_ids)
                f_ids.append(rf.fact_id)

            risks.append(
                RiskInsight(
                    category=InsightCategory.REQUIREMENT_AMBIGUITY,
                    title="Multiple Divergent Unit Configurations Requested",
                    description=f"Customer referenced conflicting configurations ({', '.join(sorted(unit_types))}) without final selection.",
                    impact_description="Inventory recommendation cannot be locked down accurately.",
                    priority=InsightPriority.MEDIUM,
                    confidence=0.91,
                    evidence=InsightEvidence(
                        source_message_ids=list(dict.fromkeys(all_msgs)),
                        fact_ids=f_ids,
                        text_snippets=list(unit_types),
                        extraction_method="DETERMINISTIC_REQUIREMENT_PATTERN_CONFLICT",
                    ),
                )
            )

        for rf in req_facts:
            val_str = str(rf.value).lower()
            if any(term in val_str for term in ("not sure", "maybe", "confused", "undecided", "flexible")):
                risks.append(
                    RiskInsight(
                        category=InsightCategory.REQUIREMENT_AMBIGUITY,
                        title="Undecided / Ambiguous Property Requirement",
                        description=f"Customer expressed ambiguity regarding configuration: '{rf.value}'",
                        impact_description="Requirement definition needs further consultative discovery.",
                        priority=InsightPriority.MEDIUM,
                        confidence=0.88,
                        evidence=InsightEvidence(
                            source_message_ids=rf.source_message_ids,
                            fact_ids=[rf.fact_id],
                            text_snippets=[str(rf.value)],
                            extraction_method="DETERMINISTIC_REQUIREMENT_AMBIGUITY_DETECTION",
                        ),
                    )
                )

        return risks


class CommunicationGapRiskDetector(AbstractRiskDetector):
    """Detects communication breakdowns, objections unhandled, or engagement friction."""

    @property
    def detector_name(self) -> str:
        return "CommunicationGapRiskDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.COMMUNICATION_GAP}

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        risks: List[RiskInsight] = []
        events = context.get_events()

        # Check if an objection was raised but no OBJECTION_HANDLED milestone or follow-up occurred
        objections = [e for e in events if e.event_type == TimelineEventType.OBJECTION_RAISED]
        handled_milestones = [m for m in context.get_milestones() if "OBJECTION" in m.milestone_type.value]

        if objections and not handled_milestones:
            for obj in objections:
                risks.append(
                    RiskInsight(
                        category=InsightCategory.COMMUNICATION_GAP,
                        title=f"Unhandled Customer Objection: {obj.title}",
                        description=f"An objection was logged ('{obj.description}') with no recorded resolution in the timeline.",
                        impact_description="Buyer hesitation persists unaddressed.",
                        priority=InsightPriority.HIGH,
                        confidence=0.93,
                        evidence=InsightEvidence(
                            source_message_ids=obj.provenance.source_message_ids,
                            source_event_ids=[obj.event_id],
                            text_snippets=[obj.description],
                            extraction_method="DETERMINISTIC_UNRESOLVED_OBJECTION_MAPPING",
                        ),
                    )
                )

        return risks


class CustomRiskDetector(AbstractRiskDetector):
    """Configurable detector allowing dynamic registration of custom risk logic."""

    def __init__(
        self,
        name: str,
        category: InsightCategory = InsightCategory.CUSTOM_RISK,
        eval_fn: Optional[Callable[[ConversationInsightContext], List[RiskInsight]]] = None,
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

    def detect(self, context: ConversationInsightContext) -> List[RiskInsight]:
        if self._eval_fn:
            return self._eval_fn(context)
        return []


def register_standard_risk_detectors(registry: RiskDetectorRegistry) -> None:
    """Registers all 8 standard risk detectors into the registry."""
    registry.register(MissingInformationRiskDetector())
    registry.register(UnansweredQuestionRiskDetector())
    registry.register(MissingDocumentRiskDetector())
    registry.register(DelayedResponseRiskDetector())
    registry.register(BudgetGapRiskDetector())
    registry.register(TimelineConflictRiskDetector())
    registry.register(RequirementAmbiguityRiskDetector())
    registry.register(CommunicationGapRiskDetector())


# Populate default singleton registry
register_standard_risk_detectors(default_risk_detector_registry)
