"""
HunterOS Engage V1 - Core Rule Pack
Standard cross-industry intent detection rules.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.timeline.models import (
    ImportantMomentType,
    MilestoneType,
    TimelineEventCategory,
    TimelineEventType,
)
from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionMethod,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack


class InformationRequestRule(AbstractIntentRule):
    """Detects requests for information, details, or questions."""

    @property
    def rule_name(self) -> str:
        return "Core_InformationRequestRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.INFORMATION_REQUEST]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        facts = context.get_facts()

        info_events = [
            e for e in events
            if e.event_type in (TimelineEventType.QUESTION_ASKED, TimelineEventType.INFORMATION_SHARED)
            or (e.category == TimelineEventCategory.COMMUNICATION and "?" in e.description)
            or any(k in e.description.lower() for k in ("what is", "tell me about", "details", "information", "how does", "specifications"))
        ]
        for ev in info_events:
            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.90,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.INFORMATION_REQUEST,
                    title=f"Information Request: {ev.title}",
                    description=f"Customer seeking information: '{ev.description}'",
                    confidence=0.90,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        question_facts = [
            f for f in facts
            if getattr(f, "fact_type", "").lower() in ("question", "inquiry")
            or "?" in getattr(f, "raw_value", "")
            or "?" in getattr(f, "value", "")
        ]
        for qf in question_facts:
            src_msgs = getattr(qf, "source_message_ids", []) or []
            val = getattr(qf, "raw_value", "") or getattr(qf, "value", "") or getattr(qf, "statement", "") or ""
            evidence = IntentEvidence(
                source_message_ids=src_msgs,
                source_fact_ids=[qf.fact_id],
                text_snippets=[val],
                detection_method=IntentDetectionMethod.FACT_MATCHING,
                confidence_score=0.88,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.INFORMATION_REQUEST,
                    title=f"Information Request Fact: {val[:40]}",
                    description=f"Observed customer inquiry: '{val}'",
                    confidence=0.88,
                    detection_method=IntentDetectionMethod.FACT_MATCHING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        return intents


class GeneralInquiryRule(AbstractIntentRule):
    """Detects broad introductory or general inquiries."""

    @property
    def rule_name(self) -> str:
        return "Core_GeneralInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.GENERAL_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        intro_events = [
            e for e in events
            if e.event_type == TimelineEventType.CUSTOMER_INTRODUCED
            or (e.category == TimelineEventCategory.COMMUNICATION and any(k in e.description.lower() for k in ("hi", "hello", "looking for", "inquiry", "interested in")))
        ]
        for ev in intro_events:
            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.85,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.GENERAL_INQUIRY,
                    title="General Inquiry",
                    description=f"Introductory customer engagement: '{ev.description}'",
                    confidence=0.85,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        return intents


class SupportRequestRule(AbstractIntentRule):
    """Detects support assistance requests."""

    @property
    def rule_name(self) -> str:
        return "Core_SupportRequestRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.SUPPORT_REQUEST]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        support_keywords = ("support", "help", "issue", "assistance", "problem", "ticket", "service request")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in support_keywords):
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.91,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.SUPPORT_REQUEST,
                        title=f"Support Request: {ev.title}",
                        description=f"Customer requested support assistance: '{ev.description}'",
                        confidence=0.91,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="CoreRulePack",
                    )
                )

        return intents


class ComplaintRule(AbstractIntentRule):
    """Detects customer grievances and complaints."""

    @property
    def rule_name(self) -> str:
        return "Core_ComplaintRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.COMPLAINT]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        risks = context.get_risks()

        complaint_events = [
            e for e in events
            if e.event_type == TimelineEventType.OBJECTION_RAISED
            or e.category == TimelineEventCategory.OBJECTION
            or any(k in e.description.lower() for k in ("complaint", "dissatisfied", "unacceptable", "delay", "poor service", "escalate", "frustrated"))
        ]
        for ev in complaint_events:
            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.94,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.COMPLAINT,
                    title=f"Customer Complaint: {ev.title}",
                    description=f"Grievance or dissatisfaction raised: '{ev.description}'",
                    confidence=0.94,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                    business_importance=BusinessImportance.CRITICAL_COMMUNICATION,
                )
            )

        comm_risks = [r for r in risks if "communication" in r.title.lower() or "delayed" in r.title.lower()]
        for cr in comm_risks:
            r_id = getattr(cr, "risk_id", None) or getattr(cr, "insight_id", None)
            evidence = IntentEvidence(
                source_message_ids=cr.evidence.source_message_ids,
                source_insight_ids=[r_id] if r_id else [],
                text_snippets=cr.evidence.text_snippets,
                detection_method=IntentDetectionMethod.INSIGHT_DERIVED,
                confidence_score=0.89,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.COMPLAINT,
                    title=f"Complaint Risk: {cr.title}",
                    description=f"Derived from communication breakdown risk: '{cr.description}'",
                    confidence=0.89,
                    detection_method=IntentDetectionMethod.INSIGHT_DERIVED,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                    business_importance=BusinessImportance.CRITICAL_COMMUNICATION,
                )
            )

        return intents


class ReferralRule(AbstractIntentRule):
    """Detects referrals made by or requested for external parties."""

    @property
    def rule_name(self) -> str:
        return "Core_ReferralRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.REFERRAL]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        referral_keywords = ("refer", "referral", "friend", "colleague", "brother", "relative", "someone looking for")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in referral_keywords):
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.92,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.REFERRAL,
                        title=f"Referral Intent: {ev.title}",
                        description=f"Customer referring an acquaintance: '{ev.description}'",
                        confidence=0.92,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="CoreRulePack",
                    )
                )

        return intents


class ScheduleMeetingRule(AbstractIntentRule):
    """Detects intent to schedule a call, consultation, or meeting."""

    @property
    def rule_name(self) -> str:
        return "Core_ScheduleMeetingRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.SCHEDULE_MEETING]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        milestones = context.get_milestones()

        meeting_events = [
            e for e in events
            if e.event_type == TimelineEventType.MEETING_SCHEDULED
            or (e.category == TimelineEventCategory.SCHEDULING and any(k in e.description.lower() for k in ("call", "meeting", "zoom", "meet", "consultation")))
        ]
        for ev in meeting_events:
            # Check if this is exclusively a site visit vs a general meeting
            if "site visit" in ev.description.lower() or "sample flat" in ev.description.lower():
                continue

            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.96,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.SCHEDULE_MEETING,
                    title=f"Schedule Meeting: {ev.title}",
                    description=f"Customer scheduled consultation or meeting: '{ev.description}'",
                    confidence=0.96,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        meeting_milestones = [
            m for m in milestones
            if m.milestone_type == MilestoneType.APPOINTMENT_COMMITTED
            and "visit" not in m.title.lower()
        ]
        for mm in meeting_milestones:
            ev_ids = getattr(mm, "source_event_ids", []) or getattr(mm, "supporting_event_ids", [])
            evidence = IntentEvidence(
                source_event_ids=list(ev_ids),
                source_milestone_ids=[mm.milestone_id],
                text_snippets=[mm.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.98,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.SCHEDULE_MEETING,
                    title=f"Meeting Milestone: {mm.title}",
                    description=f"Confirmed milestone meeting: '{mm.description}'",
                    confidence=0.98,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        return intents


class DocumentRequestRule(AbstractIntentRule):
    """Detects requests for brochures, documents, PDFs, or collateral."""

    @property
    def rule_name(self) -> str:
        return "Core_DocumentRequestRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.DOCUMENT_REQUEST]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        facts = context.get_facts()
        actions = context.get_actions()

        doc_events = [
            e for e in events
            if e.event_type == TimelineEventType.DOCUMENT_SHARED
            or e.category == TimelineEventCategory.DOCUMENT
            or any(k in e.description.lower() for k in ("brochure", "floor plan", "catalogue", "document", "pdf", "sheet", "noc", "sanction plan", "email the"))
        ]
        for ev in doc_events:
            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.95,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.DOCUMENT_REQUEST,
                    title=f"Document Request: {ev.title}",
                    description=f"Customer requested documentation: '{ev.description}'",
                    confidence=0.95,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        doc_facts = [
            f for f in facts
            if getattr(f, "category", None) in (FactCategory.DOCUMENT_MENTIONED, "DOCUMENT_MENTIONED")
            or "document" in getattr(f, "fact_type", "").lower()
            or any(k in getattr(f, "key", "").lower() for k in ("document", "brochure", "floor_plan", "pdf"))
        ]
        for df in doc_facts:
            src_msgs = getattr(df, "source_message_ids", []) or []
            val = getattr(df, "raw_value", "") or getattr(df, "value", "") or getattr(df, "statement", "") or ""
            evidence = IntentEvidence(
                source_message_ids=src_msgs,
                source_fact_ids=[df.fact_id],
                text_snippets=[val],
                detection_method=IntentDetectionMethod.FACT_MATCHING,
                confidence_score=0.92,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.DOCUMENT_REQUEST,
                    title=f"Document Fact: {val[:40]}",
                    description=f"Referenced document collateral: '{val}'",
                    confidence=0.92,
                    detection_method=IntentDetectionMethod.FACT_MATCHING,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        doc_actions = [
            a for a in actions
            if any(k in a.title.lower() for k in ("document", "brochure", "floor plan", "pdf", "send", "email", "share"))
        ]
        for da in doc_actions:
            a_id = getattr(da, "action_id", None) or getattr(da, "insight_id", None)
            evidence = IntentEvidence(
                source_message_ids=da.evidence.source_message_ids,
                source_insight_ids=[a_id] if a_id else [],
                text_snippets=da.evidence.text_snippets,
                detection_method=IntentDetectionMethod.INSIGHT_DERIVED,
                confidence_score=0.93,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.DOCUMENT_REQUEST,
                    title=f"Document Action Intent: {da.title}",
                    description=f"Actionable document requirement: '{da.description}'",
                    confidence=0.93,
                    detection_method=IntentDetectionMethod.INSIGHT_DERIVED,
                    evidence=evidence,
                    rule_pack_name="CoreRulePack",
                )
            )

        return intents


class CustomIntentRule(AbstractIntentRule):
    """Extensible rule capable of executing custom evaluation functions."""

    def __init__(
        self,
        name: str = "Core_CustomIntentRule",
        evaluator_fn: Optional[Callable[[IntentDetectionContext], List[DetectedIntent]]] = None,
    ):
        self._name = name
        self._evaluator_fn = evaluator_fn

    @property
    def rule_name(self) -> str:
        return self._name

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.CUSTOM_INTENT]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        if self._evaluator_fn:
            return self._evaluator_fn(context)
        return []


class CoreRulePack(AbstractRulePack):
    """Core industry-agnostic rule pack."""

    @property
    def pack_name(self) -> str:
        return "CoreRulePack"

    @property
    def description(self) -> str:
        return "Standard cross-industry intent rules (Information, Meeting, Support, Complaint, Referral, Document, Custom)."

    def get_rules(self) -> List[AbstractIntentRule]:
        return [
            InformationRequestRule(),
            GeneralInquiryRule(),
            SupportRequestRule(),
            ComplaintRule(),
            ReferralRule(),
            ScheduleMeetingRule(),
            DocumentRequestRule(),
            CustomIntentRule(),
        ]
