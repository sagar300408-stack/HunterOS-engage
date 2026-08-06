"""
HunterOS Engage V1 - Standard Opportunity Detectors
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Deterministic opportunity detectors evaluating Conversation Analysis
and Conversation Timeline artifacts with complete lineage evidence.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from app.domain.conversations.analysis.models import FactCategory
from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.opportunities.base import AbstractOpportunityDetector
from app.domain.conversations.insight.detectors.opportunities.registry import (
    OpportunityDetectorRegistry,
    default_opportunity_detector_registry,
)
from app.domain.conversations.insight.models import (
    InsightCategory,
    InsightEvidence,
    InsightPriority,
    OpportunityInsight,
)
from app.domain.conversations.timeline.models import ImportantMomentType, TimelineEventType


class UpsellOpportunityDetector(AbstractOpportunityDetector):
    """Detects opportunities for premium tier, larger configurations, or luxury upgrades."""

    @property
    def detector_name(self) -> str:
        return "UpsellOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.UPSELL}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()
        events = context.get_events()

        # Check for premium keywords in facts
        premium_keywords = ("penthouse", "luxury", "duplex", "sky villa", "sea view", "top floor", "corner unit", "premium")
        for f in facts:
            val_str = str(f.value).lower()
            matched = [k for k in premium_keywords if k in val_str]
            if matched:
                opportunities.append(
                    OpportunityInsight(
                        category=InsightCategory.UPSELL,
                        title=f"Premium Inventory Interest: {', '.join(matched).title()}",
                        description=f"Customer expressed explicit interest in premium inventory attributes: '{f.value}'",
                        value_potential="High margin upgrade potential / higher ASP inventory positioning.",
                        qualification_criteria=["Buyer interest in premium specification"],
                        priority=InsightPriority.HIGH,
                        confidence=0.94,
                        evidence=InsightEvidence(
                            source_message_ids=f.source_message_ids,
                            fact_ids=[f.fact_id],
                            text_snippets=[str(f.value)],
                            extraction_method="DETERMINISTIC_PREMIUM_KEYWORD_MATCH",
                        ),
                    )
                )

        # Check for flexible or high budget indicators
        for f in facts:
            if f.category == FactCategory.BUDGET_REFERENCE:
                val_str = str(f.value).lower()
                if any(t in val_str for t in ("flexible", "stretch", "no upper limit", "open to higher")):
                    opportunities.append(
                        OpportunityInsight(
                            category=InsightCategory.UPSELL,
                            title="Flexible Buyer Budget Observed",
                            description=f"Customer expressed financial flexibility regarding unit pricing: '{f.value}'",
                            value_potential="Potential to showcase next-tier floor plans or larger unit sizes.",
                            qualification_criteria=["Flexible purchasing capacity"],
                            priority=InsightPriority.HIGH,
                            confidence=0.92,
                            evidence=InsightEvidence(
                                source_message_ids=f.source_message_ids,
                                fact_ids=[f.fact_id],
                                text_snippets=[str(f.value)],
                                extraction_method="DETERMINISTIC_BUDGET_FLEXIBILITY_MATCH",
                            ),
                        )
                    )

        return opportunities


class CrossSellOpportunityDetector(AbstractOpportunityDetector):
    """Detects multi-location, auxiliary service, or cross-category opportunities."""

    @property
    def detector_name(self) -> str:
        return "CrossSellOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.CROSS_SELL}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()
        topics = context.get_topics()

        # Check for multi-city / multiple property mentions
        loc_facts = [f for f in facts if f.category == FactCategory.LOCATION_REFERENCE]
        if len(loc_facts) >= 2:
            locations = [str(f.value) for f in loc_facts]
            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.CROSS_SELL,
                    title="Multi-Location Interest Identified",
                    description=f"Customer discussed properties across multiple locations: {', '.join(locations)}.",
                    value_potential="Cross-project portfolio presentation potential.",
                    qualification_criteria=["Multi-market interest"],
                    priority=InsightPriority.MEDIUM,
                    confidence=0.88,
                    evidence=InsightEvidence(
                        source_message_ids=[mid for f in loc_facts for mid in f.source_message_ids],
                        fact_ids=[f.fact_id for f in loc_facts],
                        text_snippets=locations,
                        extraction_method="DETERMINISTIC_MULTI_LOCATION_EXTRACTION",
                    ),
                )
            )

        # Check for service keywords (interior, home loan, legal, rental management)
        service_keywords = ("interior", "home loan", "mortgage", "rental", "lease", "tenant", "resale")
        for f in facts:
            val_str = str(f.value).lower()
            matched = [sk for sk in service_keywords if sk in val_str]
            if matched:
                opportunities.append(
                    OpportunityInsight(
                        category=InsightCategory.CROSS_SELL,
                        title=f"Auxiliary Value Service: {', '.join(matched).title()}",
                        description=f"Customer referenced auxiliary ecosystem service requirements: '{f.value}'",
                        value_potential="Ancillary revenue generation & ecosystem cross-sell.",
                        qualification_criteria=[f"Inquiring about {', '.join(matched)}"],
                        priority=InsightPriority.MEDIUM,
                        confidence=0.90,
                        evidence=InsightEvidence(
                            source_message_ids=f.source_message_ids,
                            fact_ids=[f.fact_id],
                            text_snippets=[str(f.value)],
                            extraction_method="DETERMINISTIC_SERVICE_KEYWORD_MATCH",
                        ),
                    )
                )

        return opportunities


class AdditionalRequirementOpportunityDetector(AbstractOpportunityDetector):
    """Detects auxiliary unit requirements or specific feature enhancements."""

    @property
    def detector_name(self) -> str:
        return "AdditionalRequirementOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.ADDITIONAL_REQUIREMENT}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()
        req_facts = [f for f in facts if f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE)]

        amenity_terms = ("balcony", "study", "servant room", "pooja room", "terrace", "garden", "ev charger", "vastu")
        for rf in req_facts:
            val_str = str(rf.value).lower()
            matched = [term for term in amenity_terms if term in val_str]
            if matched:
                opportunities.append(
                    OpportunityInsight(
                        category=InsightCategory.ADDITIONAL_REQUIREMENT,
                        title=f"Specific Feature Requirement: {', '.join(matched).title()}",
                        description=f"Customer highlighted specific unit features: '{rf.value}'",
                        value_potential="Tailored unit curation increasing conversion probability.",
                        qualification_criteria=[f"Requires {', '.join(matched)}"],
                        priority=InsightPriority.MEDIUM,
                        confidence=0.91,
                        evidence=InsightEvidence(
                            source_message_ids=rf.source_message_ids,
                            fact_ids=[rf.fact_id],
                            text_snippets=[str(rf.value)],
                            extraction_method="DETERMINISTIC_AMENITY_TERM_MATCH",
                        ),
                    )
                )

        return opportunities


class FollowUpOpportunityDetector(AbstractOpportunityDetector):
    """Detects high-receptivity moments for structured follow-up touchpoints."""

    @property
    def detector_name(self) -> str:
        return "FollowUpOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.FOLLOW_UP}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        events = context.get_events()
        moments = context.get_moments()

        # Follow-up opportunity on commitment moment or agreement event
        commitment_moments = [m for m in moments if m.moment_type == ImportantMomentType.FIRST_COMMITMENT]
        for cm in commitment_moments:
            ev_ids = [cm.source_event_id] if cm.source_event_id else []
            msg_ids = [cm.source_message_id] if cm.source_message_id else []
            snippets = [cm.snippet] if cm.snippet else ([cm.significance] if cm.significance else [])
            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.FOLLOW_UP,
                    title="High-Receptivity Commitment Follow-Up",
                    description=f"Customer reached a commitment moment: '{cm.title}' - '{cm.significance}'",
                    value_potential="Timely follow-up capitalizes on strong buyer momentum.",
                    qualification_criteria=["Explicit customer commitment observed"],
                    priority=InsightPriority.HIGH,
                    confidence=0.96,
                    evidence=InsightEvidence(
                        source_moment_ids=[cm.moment_id],
                        source_event_ids=ev_ids,
                        source_message_ids=msg_ids,
                        text_snippets=snippets,
                        extraction_method="DETERMINISTIC_COMMITMENT_MOMENT_EXPANSION",
                    ),
                )
            )

        followup_events = [e for e in events if e.event_type in (TimelineEventType.FOLLOW_UP_REQUESTED, TimelineEventType.CUSTOM_EVENT)]
        for fe in followup_events:
            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.FOLLOW_UP,
                    title=f"Scheduled Follow-Up Touchpoint: {fe.title}",
                    description=f"A follow-up event was logged: '{fe.description}'",
                    value_potential="Structured progression through buyer evaluation.",
                    qualification_criteria=["Follow-up scheduled"],
                    priority=InsightPriority.MEDIUM,
                    confidence=0.93,
                    evidence=InsightEvidence(
                        source_message_ids=fe.provenance.source_message_ids if fe.provenance else [],
                        source_event_ids=[fe.event_id],
                        text_snippets=[fe.description],
                        extraction_method="DETERMINISTIC_FOLLOWUP_EVENT_MAPPING",
                    ),
                )
            )

        return opportunities


class DocumentSharingOpportunityDetector(AbstractOpportunityDetector):
    """Detects opportunities to provide collateral, floor plans, or pricing matrices."""

    @property
    def detector_name(self) -> str:
        return "DocumentSharingOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.DOCUMENT_SHARING}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()
        events = context.get_events()

        # If requirements exist and no document has been shared yet
        req_facts = [f for f in facts if f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE)]
        has_doc_shared = any(e.event_type == TimelineEventType.DOCUMENT_SHARED for e in events)

        if req_facts and not has_doc_shared:
            f = req_facts[0]
            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.DOCUMENT_SHARING,
                    title="Collateral & Floor Plan Sharing Opportunity",
                    description="Customer requirements are defined; sharing comprehensive brochures or floor plans provides immediate value.",
                    value_potential="Enables customer self-review and accelerates decision velocity.",
                    qualification_criteria=["Requirements stated, collateral not yet dispatched"],
                    priority=InsightPriority.MEDIUM,
                    confidence=0.89,
                    evidence=InsightEvidence(
                        source_message_ids=f.source_message_ids,
                        fact_ids=[f.fact_id],
                        text_snippets=[str(f.value)],
                        extraction_method="DETERMINISTIC_UNSHARED_COLLATERAL_OPPORTUNITY",
                    ),
                )
            )

        return opportunities


class MeetingOpportunityDetector(AbstractOpportunityDetector):
    """Detects opportunities to propose an in-person site visit or walkthrough."""

    @property
    def detector_name(self) -> str:
        return "MeetingOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.MEETING}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()
        events = context.get_events()

        has_meeting = any(e.event_type == TimelineEventType.MEETING_SCHEDULED for e in events)
        has_budget = any(f.category == FactCategory.BUDGET_REFERENCE for f in facts)
        has_req = any(f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE) for f in facts)

        # If budget and requirements are established but no site visit is booked
        if has_budget and has_req and not has_meeting:
            b_fact = next(f for f in facts if f.category == FactCategory.BUDGET_REFERENCE)
            r_fact = next(f for f in facts if f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE))
            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.MEETING,
                    title="Site Visit / In-Person Demo Opportunity",
                    description="Customer has aligned budget and requirements without an active site visit booking.",
                    value_potential="Site visits convert at significantly higher rates.",
                    qualification_criteria=["Budget and Requirements aligned"],
                    priority=InsightPriority.HIGH,
                    confidence=0.91,
                    evidence=InsightEvidence(
                        source_message_ids=b_fact.source_message_ids + r_fact.source_message_ids,
                        fact_ids=[b_fact.fact_id, r_fact.fact_id],
                        text_snippets=[f"Budget: {b_fact.value}", f"Req: {r_fact.value}"],
                        extraction_method="DETERMINISTIC_QUALIFIED_MEETING_READINESS",
                    ),
                )
            )

        return opportunities


class QualificationOpportunityDetector(AbstractOpportunityDetector):
    """Detects high-readiness qualified leads based on multi-attribute completeness."""

    @property
    def detector_name(self) -> str:
        return "QualificationOpportunityDetector"

    @property
    def supported_categories(self) -> Set[InsightCategory]:
        return {InsightCategory.QUALIFICATION}

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        opportunities: List[OpportunityInsight] = []
        facts = context.get_facts()

        has_contact = any(f.category == FactCategory.CONTACT_INFO for f in facts)
        has_budget = any(f.category == FactCategory.BUDGET_REFERENCE for f in facts)
        has_req = any(f.category in (FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE) for f in facts)
        has_date = any(f.category == FactCategory.DATE_REFERENCE for f in facts)

        if has_contact and has_budget and has_req:
            qual_criteria = ["Contact verified", "Budget specified", "Requirements defined"]
            if has_date:
                qual_criteria.append("Timeline stated")

            valid_cats = (FactCategory.CONTACT_INFO, FactCategory.BUDGET_REFERENCE, FactCategory.PROPERTY_REFERENCE, FactCategory.PRODUCT_REFERENCE, FactCategory.DATE_REFERENCE)
            all_f_ids = [f.fact_id for f in facts if f.category in valid_cats]
            all_msgs: List[str] = []
            for f in facts:
                if f.category in valid_cats:
                    all_msgs.extend(f.source_message_ids)

            opportunities.append(
                OpportunityInsight(
                    category=InsightCategory.QUALIFICATION,
                    title="Fully Qualified Buyer Profile Observed",
                    description=f"Conversation artifacts contain complete qualification pillars ({', '.join(qual_criteria)}).",
                    value_potential="High conversion velocity prospect suitable for dedicated account prioritization.",
                    qualification_criteria=qual_criteria,
                    priority=InsightPriority.HIGH,
                    confidence=0.97,
                    evidence=InsightEvidence(
                        source_message_ids=list(dict.fromkeys(all_msgs)),
                        fact_ids=all_f_ids,
                        text_snippets=qual_criteria,
                        extraction_method="DETERMINISTIC_MULTI_PILLAR_QUALIFICATION",
                    ),
                )
            )

        return opportunities


class CustomOpportunityDetector(AbstractOpportunityDetector):
    """Configurable detector allowing dynamic registration of custom opportunity rules."""

    def __init__(
        self,
        name: str,
        category: InsightCategory = InsightCategory.CUSTOM_OPPORTUNITY,
        eval_fn: Optional[Callable[[ConversationInsightContext], List[OpportunityInsight]]] = None,
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

    def detect(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        if self._eval_fn:
            return self._eval_fn(context)
        return []


def register_standard_opportunity_detectors(registry: OpportunityDetectorRegistry) -> None:
    """Registers all 7 standard opportunity detectors into the registry."""
    registry.register(UpsellOpportunityDetector())
    registry.register(CrossSellOpportunityDetector())
    registry.register(AdditionalRequirementOpportunityDetector())
    registry.register(FollowUpOpportunityDetector())
    registry.register(DocumentSharingOpportunityDetector())
    registry.register(MeetingOpportunityDetector())
    registry.register(QualificationOpportunityDetector())


# Populate default singleton registry
register_standard_opportunity_detectors(default_opportunity_detector_registry)
