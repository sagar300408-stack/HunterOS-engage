"""
HunterOS Engage V1 - Real Estate Rule Pack
Specialized intent detection rules for the real estate and property vertical.
"""

from __future__ import annotations

from typing import List, Optional

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.timeline.models import (
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
    IntentType,
)
from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack


class PropertyInquiryRule(AbstractIntentRule):
    """Detects inquiries regarding specific properties, configurations, units, or locations."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_PropertyInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.PROPERTY_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        facts = context.get_facts()

        req_keywords = ("bhk", "apartment", "villa", "flat", "plot", "sqft", "tower", "layout", "unit", "property")

        req_events = [
            e for e in events
            if e.event_type == TimelineEventType.REQUIREMENT_IDENTIFIED
            or e.category == TimelineEventCategory.REQUIREMENT
            or any(k in e.description.lower() for k in req_keywords)
        ]
        for ev in req_events:
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
                    intent_type=IntentType.PROPERTY_INQUIRY,
                    title=f"Property Inquiry: {ev.title}",
                    description=f"Customer expressed property specifications: '{ev.description}'",
                    confidence=0.94,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        property_facts = [
            f for f in facts
            if getattr(f, "category", None) in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE, FactCategory.LOCATION_REFERENCE, "PROPERTY_REFERENCE", "PRODUCT_REFERENCE", "LOCATION_REFERENCE")
            or getattr(f, "fact_type", "").lower() in ("requirement", "property", "configuration", "location")
            or any(k in getattr(f, "key", "").lower() for k in ("property", "bhk", "unit", "requirement", "location"))
        ]
        for pf in property_facts:
            src_msgs = getattr(pf, "source_message_ids", []) or []
            val = getattr(pf, "raw_value", "") or getattr(pf, "value", "") or getattr(pf, "statement", "") or ""
            evidence = IntentEvidence(
                source_message_ids=src_msgs,
                source_fact_ids=[pf.fact_id],
                text_snippets=[val],
                detection_method=IntentDetectionMethod.FACT_MATCHING,
                confidence_score=0.92,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.PROPERTY_INQUIRY,
                    title=f"Property Spec: {val[:40]}",
                    description=f"Property specification requirement: '{val}'",
                    confidence=0.92,
                    detection_method=IntentDetectionMethod.FACT_MATCHING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        return intents


class ProductInquiryRule(AbstractIntentRule):
    """Detects product or inventory-level inquiries."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_ProductInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.PRODUCT_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        product_keywords = ("catalog", "product", "features", "amenities", "specifications", "furnishing")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in product_keywords) and ev.event_type != TimelineEventType.REQUIREMENT_IDENTIFIED:
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.88,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.PRODUCT_INQUIRY,
                        title=f"Product / Amenity Inquiry: {ev.title}",
                        description=f"Inquiry into project offerings and specifications: '{ev.description}'",
                        confidence=0.88,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class PricingInquiryRule(AbstractIntentRule):
    """Detects price and cost inquiries."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_PricingInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.PRICING_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        pricing_keywords = ("price", "cost", "quote", "rate", "how much", "charges", "rate card", "price list")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in pricing_keywords) and ev.event_type != TimelineEventType.BUDGET_MENTIONED:
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.93,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.PRICING_INQUIRY,
                        title=f"Pricing Inquiry: {ev.title}",
                        description=f"Customer queried pricing: '{ev.description}'",
                        confidence=0.93,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class BudgetDiscussionRule(AbstractIntentRule):
    """Detects customer budget declarations, ranges, and affordability discussions."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_BudgetDiscussionRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.BUDGET_DISCUSSION]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        milestones = context.get_milestones()
        facts = context.get_facts()

        budget_events = [
            e for e in events
            if e.event_type == TimelineEventType.BUDGET_MENTIONED
            or e.category == TimelineEventCategory.FINANCIAL
            or "budget" in e.description.lower()
            or "crore" in e.description.lower()
            or "lakh" in e.description.lower()
        ]
        for ev in budget_events:
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
                    intent_type=IntentType.BUDGET_DISCUSSION,
                    title=f"Budget Discussion: {ev.title}",
                    description=f"Customer discussed budget: '{ev.description}'",
                    confidence=0.95,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        budget_milestones = [m for m in milestones if m.milestone_type == MilestoneType.BUDGET_ESTABLISHED]
        for bm in budget_milestones:
            ev_ids = getattr(bm, "source_event_ids", []) or getattr(bm, "supporting_event_ids", [])
            evidence = IntentEvidence(
                source_event_ids=list(ev_ids),
                source_milestone_ids=[bm.milestone_id],
                text_snippets=[bm.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.97,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.BUDGET_DISCUSSION,
                    title=f"Budget Established Milestone: {bm.title}",
                    description=f"Confirmed budget milestone: '{bm.description}'",
                    confidence=0.97,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        budget_facts = [
            f for f in facts
            if getattr(f, "category", None) in (FactCategory.BUDGET_REFERENCE, "BUDGET_REFERENCE")
            or getattr(f, "fact_type", "").lower() in ("budget", "financial_limit")
            or "budget" in getattr(f, "key", "").lower()
        ]
        for bf in budget_facts:
            src_msgs = getattr(bf, "source_message_ids", []) or []
            val = getattr(bf, "raw_value", "") or getattr(bf, "value", "") or getattr(bf, "statement", "") or ""
            evidence = IntentEvidence(
                source_message_ids=src_msgs,
                source_fact_ids=[bf.fact_id],
                text_snippets=[val],
                detection_method=IntentDetectionMethod.FACT_MATCHING,
                confidence_score=0.94,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.BUDGET_DISCUSSION,
                    title=f"Budget Fact: {val[:40]}",
                    description=f"Budget declaration fact: '{val}'",
                    confidence=0.94,
                    detection_method=IntentDetectionMethod.FACT_MATCHING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        return intents


class ScheduleSiteVisitRule(AbstractIntentRule):
    """Detects site visit scheduling, walkthrough requests, and physical inspection intents."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_ScheduleSiteVisitRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.SCHEDULE_SITE_VISIT]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        visit_events = [
            e for e in events
            if "site visit" in e.description.lower()
            or "visit site" in e.description.lower()
            or "sample flat" in e.description.lower()
            or "walkthrough" in e.description.lower()
            or "inspection" in e.description.lower()
        ]
        for ev in visit_events:
            evidence = IntentEvidence(
                source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                source_event_ids=[ev.event_id],
                text_snippets=[ev.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.97,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.SCHEDULE_SITE_VISIT,
                    title=f"Schedule Site Visit: {ev.title}",
                    description=f"Customer scheduled or requested site visit: '{ev.description}'",
                    confidence=0.97,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        return intents


class ProposalRequestRule(AbstractIntentRule):
    """Detects formal proposals, quote requests, or cost sheet demands."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_ProposalRequestRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.PROPOSAL_REQUEST]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        proposal_keywords = ("proposal", "cost sheet", "payment schedule", "formal quote", "commercial proposal")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in proposal_keywords):
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.93,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.PROPOSAL_REQUEST,
                        title=f"Proposal Request: {ev.title}",
                        description=f"Customer requested commercial proposal or cost sheet: '{ev.description}'",
                        confidence=0.93,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class NegotiationRule(AbstractIntentRule):
    """Detects discount, concession, or negotiation requests."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_NegotiationRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.NEGOTIATION]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        negotiation_keywords = ("discount", "negotiate", "best price", "special offer", "concession", "reduce price", "waiver")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in negotiation_keywords):
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
                        intent_type=IntentType.NEGOTIATION,
                        title=f"Negotiation Intent: {ev.title}",
                        description=f"Customer requesting commercial discount or negotiation: '{ev.description}'",
                        confidence=0.91,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class FinanceInquiryRule(AbstractIntentRule):
    """Detects loan, mortgage, and EMI queries."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_FinanceInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.FINANCE_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        finance_keywords = ("loan", "emi", "bank loan", "mortgage", "interest rate", "payment plan", "installment", "hfc")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in finance_keywords):
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
                        intent_type=IntentType.FINANCE_INQUIRY,
                        title=f"Finance Inquiry: {ev.title}",
                        description=f"Inquiry regarding financing and loan options: '{ev.description}'",
                        confidence=0.92,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class BookingInterestRule(AbstractIntentRule):
    """Detects high-intent booking, token payment, or unit reservation."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_BookingInterestRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.BOOKING_INTEREST]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()
        milestones = context.get_milestones()
        moments = context.get_moments()

        booking_events = [
            e for e in events
            if e.event_type == TimelineEventType.AGREEMENT_REACHED
            or "booking" in e.description.lower()
            or "token" in e.description.lower()
            or "reserve unit" in e.description.lower()
            or "hold unit" in e.description.lower()
        ]
        for ev in booking_events:
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
                    intent_type=IntentType.BOOKING_INTEREST,
                    title=f"Booking Interest: {ev.title}",
                    description=f"Customer indicated reservation or booking intent: '{ev.description}'",
                    confidence=0.96,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        agreement_milestones = [m for m in milestones if m.milestone_type == MilestoneType.COMMITMENT_FINALIZED]
        for am in agreement_milestones:
            ev_ids = getattr(am, "source_event_ids", []) or getattr(am, "supporting_event_ids", [])
            evidence = IntentEvidence(
                source_event_ids=list(ev_ids),
                source_milestone_ids=[am.milestone_id],
                text_snippets=[am.description],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.98,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.BOOKING_INTEREST,
                    title=f"Agreement Reached Milestone: {am.title}",
                    description=f"Confirmed booking agreement milestone: '{am.description}'",
                    confidence=0.98,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        booking_moments = [
            m for m in moments
            if "booking" in getattr(m, "title", "").lower()
            or "booking" in getattr(m, "significance", "").lower()
        ]
        for mo in booking_moments:
            ev_ids = [mo.source_event_id] if getattr(mo, "source_event_id", None) else []
            evidence = IntentEvidence(
                source_event_ids=ev_ids,
                source_moment_ids=[mo.moment_id],
                text_snippets=[mo.significance],
                detection_method=IntentDetectionMethod.EVENT_MAPPING,
                confidence_score=0.95,
            )
            intents.append(
                self.create_intent(
                    context=context,
                    intent_type=IntentType.BOOKING_INTEREST,
                    title=f"Booking Moment: {mo.title}",
                    description=f"High booking interest moment: '{mo.significance}'",
                    confidence=0.95,
                    detection_method=IntentDetectionMethod.EVENT_MAPPING,
                    evidence=evidence,
                    rule_pack_name="RealEstateRulePack",
                )
            )

        return intents


class CancellationRule(AbstractIntentRule):
    """Detects cancellation, withdrawal, or refund intents."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_CancellationRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.CANCELLATION]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        cancellation_keywords = ("cancel", "cancellation", "abort", "call off", "withdraw", "refund", "not interested anymore", "opt out")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in cancellation_keywords):
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.95,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.CANCELLATION,
                        title=f"Cancellation Intent: {ev.title}",
                        description=f"Customer requesting cancellation or withdrawal: '{ev.description}'",
                        confidence=0.95,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                        business_importance=BusinessImportance.CRITICAL_COMMUNICATION,
                    )
                )

        return intents


class InvestmentInquiryRule(AbstractIntentRule):
    """Detects inquiries focused on investment, rental yields, and ROI."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_InvestmentInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.INVESTMENT_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        investment_keywords = ("investment", "roi", "rental yield", "appreciation", "investor", "capital growth")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in investment_keywords):
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
                        intent_type=IntentType.INVESTMENT_INQUIRY,
                        title=f"Investment Inquiry: {ev.title}",
                        description=f"Inquiry focused on real estate investment and ROI: '{ev.description}'",
                        confidence=0.91,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class PartnershipInquiryRule(AbstractIntentRule):
    """Detects channel partner and broker collaboration inquiries."""

    @property
    def rule_name(self) -> str:
        return "RealEstate_PartnershipInquiryRule"

    @property
    def target_intent_types(self) -> List[IntentType]:
        return [IntentType.PARTNERSHIP_INQUIRY]

    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        intents: List[DetectedIntent] = []
        events = context.get_events()

        partner_keywords = ("channel partner", "broker", "brokerage", "partner", "agency tie up", "commission")
        for ev in events:
            desc_lower = ev.description.lower()
            if any(k in desc_lower for k in partner_keywords):
                evidence = IntentEvidence(
                    source_message_ids=ev.provenance.source_message_ids if ev.provenance else [],
                    source_event_ids=[ev.event_id],
                    text_snippets=[ev.description],
                    detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                    confidence_score=0.90,
                )
                intents.append(
                    self.create_intent(
                        context=context,
                        intent_type=IntentType.PARTNERSHIP_INQUIRY,
                        title=f"Partnership Inquiry: {ev.title}",
                        description=f"Channel partner or broker collaboration inquiry: '{ev.description}'",
                        confidence=0.90,
                        detection_method=IntentDetectionMethod.KEYWORD_MATCHING,
                        evidence=evidence,
                        rule_pack_name="RealEstateRulePack",
                    )
                )

        return intents


class RealEstateRulePack(AbstractRulePack):
    """Real estate vertical rule pack."""

    @property
    def pack_name(self) -> str:
        return "RealEstateRulePack"

    @property
    def description(self) -> str:
        return "Specialized real estate intent rules (Property, Pricing, Budget, Site Visit, Proposal, Negotiation, Finance, Booking, Cancellation, Investment, Partnership)."

    def get_rules(self) -> List[AbstractIntentRule]:
        return [
            PropertyInquiryRule(),
            ProductInquiryRule(),
            PricingInquiryRule(),
            BudgetDiscussionRule(),
            ScheduleSiteVisitRule(),
            ProposalRequestRule(),
            NegotiationRule(),
            FinanceInquiryRule(),
            BookingInterestRule(),
            CancellationRule(),
            InvestmentInquiryRule(),
            PartnershipInquiryRule(),
        ]
