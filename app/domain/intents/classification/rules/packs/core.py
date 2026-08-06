"""
HunterOS Engage V1 - Core Classification Rule Pack
Deterministic cross-industry classification rules.
"""

from __future__ import annotations

from typing import List, Optional

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.rules.base import (
    AbstractClassificationRule,
    AbstractClassificationRulePack,
    ClassificationCandidate,
)


class PricingInquiryClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="PricingInquiryClassificationRule",
            rule_version=rule_version,
            description="Classifies pricing questions into Commercial Category / Sales Qualification process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "pricing_inquiry" in canonical.canonical_name.lower() or "price" in raw or "cost" in raw or "rate" in raw:
            return ClassificationCandidate(
                category=IntentCategory.COMMERCIAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="SALES_QUALIFICATION",
                taxonomy_node_id="commercial.pricing_inquiry",
                confidence_boost=0.05,
                aliases=["PRICING_INQUIRY", "PRICE_REQUEST"],
            )
        return None


class BudgetDiscussionClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="BudgetDiscussionClassificationRule",
            rule_version=rule_version,
            description="Classifies budget discussions into Commercial Category / Sales Qualification process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "budget_discussion" in canonical.canonical_name.lower() or "budget" in raw or "afford" in raw or "range" in raw:
            return ClassificationCandidate(
                category=IntentCategory.COMMERCIAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="SALES_QUALIFICATION",
                taxonomy_node_id="commercial.budget_discussion",
                confidence_boost=0.05,
                aliases=["BUDGET_DISCUSSION", "AFFORDABILITY_CHECK"],
            )
        return None


class BookingInterestClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="BookingInterestClassificationRule",
            rule_version=rule_version,
            description="Classifies purchase / booking intent into Commercial Category / Deal Closing process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "booking_interest" in canonical.canonical_name.lower() or "booking" in raw or "purchase" in raw or "buy" in raw or "token" in raw:
            return ClassificationCandidate(
                category=IntentCategory.COMMERCIAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="DEAL_CLOSING",
                taxonomy_node_id="commercial.booking_interest",
                confidence_boost=0.08,
                aliases=["BOOKING_INTEREST", "PURCHASE_INTENT"],
            )
        return None


class NegotiationClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="NegotiationClassificationRule",
            rule_version=rule_version,
            description="Classifies negotiation / discount discussion into Commercial Category / Deal Closing process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "negotiation" in canonical.canonical_name.lower() or "discount" in raw or "negotiat" in raw or "offer" in raw:
            node_id = "commercial.negotiation.discount_discussion" if "discount" in raw else "commercial.negotiation"
            return ClassificationCandidate(
                category=IntentCategory.COMMERCIAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="DEAL_CLOSING",
                taxonomy_node_id=node_id,
                confidence_boost=0.05,
                aliases=["NEGOTIATION", "DISCOUNT_DISCUSSION"],
            )
        return None


class ProposalRequestClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="ProposalRequestClassificationRule",
            rule_version=rule_version,
            description="Classifies quotation / proposal requests into Commercial Category / Sales Qualification process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "proposal_request" in canonical.canonical_name.lower() or "proposal" in raw or "quotation" in raw or "quote" in raw:
            return ClassificationCandidate(
                category=IntentCategory.COMMERCIAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="SALES_QUALIFICATION",
                taxonomy_node_id="commercial.proposal_request",
                confidence_boost=0.05,
                aliases=["PROPOSAL_REQUEST", "QUOTE_REQUEST"],
            )
        return None


class MeetingRequestClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="MeetingRequestClassificationRule",
            rule_version=rule_version,
            description="Classifies meeting / consultation calls into Operational Category / Appointment Scheduling process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "schedule_meeting" in canonical.canonical_name.lower() or "meeting_request" in canonical.canonical_name.lower() or "call" in raw or "meeting" in raw or "consultation" in raw:
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="APPOINTMENT_SCHEDULING",
                taxonomy_node_id="operational.meeting_request",
                confidence_boost=0.05,
                aliases=["SCHEDULE_MEETING", "MEETING_REQUEST"],
            )
        return None


class SiteVisitClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="SiteVisitClassificationRule",
            rule_version=rule_version,
            description="Classifies site visit / inspection into Operational Category / Appointment Scheduling process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "schedule_site_visit" in canonical.canonical_name.lower() or "site_visit" in canonical.canonical_name.lower() or "visit" in raw or "tour" in raw:
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="APPOINTMENT_SCHEDULING",
                taxonomy_node_id="operational.site_visit",
                confidence_boost=0.05,
                aliases=["SCHEDULE_SITE_VISIT", "SITE_VISIT"],
            )
        return None


class DocumentRequestClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="DocumentRequestClassificationRule",
            rule_version=rule_version,
            description="Classifies document / brochure requests into Operational Category / Document Fulfillment process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "document_request" in canonical.canonical_name.lower() or "brochure" in raw or "pdf" in raw or "catalog" in raw or "document" in raw:
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="DOCUMENT_FULFILLMENT",
                taxonomy_node_id="operational.document_request",
                confidence_boost=0.05,
                aliases=["DOCUMENT_REQUEST", "BROCHURE_REQUEST"],
            )
        return None


class SupportRequestClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="SupportRequestClassificationRule",
            rule_version=rule_version,
            description="Classifies customer support requests into Operational Category / Customer Support process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "support_request" in canonical.canonical_name.lower() or "help" in raw or "assistance" in raw or "ticket" in raw or "support" in raw:
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="CUSTOMER_SUPPORT",
                taxonomy_node_id="operational.support_request",
                confidence_boost=0.05,
                aliases=["SUPPORT_REQUEST", "CUSTOMER_SERVICE"],
            )
        return None


class ComplaintClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="ComplaintClassificationRule",
            rule_version=rule_version,
            description="Classifies complaints / grievances into Relationship Category / Customer Support process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "complaint" in canonical.canonical_name.lower() or "grievance" in raw or "dissatisfied" in raw or "unhappy" in raw:
            return ClassificationCandidate(
                category=IntentCategory.RELATIONSHIP,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="CUSTOMER_SUPPORT",
                taxonomy_node_id="relationship.complaint",
                confidence_boost=0.08,
                aliases=["COMPLAINT", "ESCALATION"],
            )
        return None


class ReferralClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="ReferralClassificationRule",
            rule_version=rule_version,
            description="Classifies referrals / partnerships into Relationship Category / Retention process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "referral" in canonical.canonical_name.lower() or "refer" in raw or "friend" in raw or "colleague" in raw or "partner" in raw:
            node_id = "relationship.partnership" if "partner" in raw else "relationship.referral"
            return ClassificationCandidate(
                category=IntentCategory.RELATIONSHIP,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="RETENTION_RELATIONSHIP",
                taxonomy_node_id=node_id,
                confidence_boost=0.05,
                aliases=["REFERRAL", "PARTNERSHIP"],
            )
        return None


class GeneralInquiryClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="GeneralInquiryClassificationRule",
            rule_version=rule_version,
            description="Classifies general inquiries and product questions into Information Category / General Discovery process.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "general_inquiry" in canonical.canonical_name.lower() or "product_inquiry" in canonical.canonical_name.lower() or "hello" in raw or "hi" in raw or "info" in raw:
            node_id = "information.product_inquiry" if "product" in raw else "information.general_inquiry"
            return ClassificationCandidate(
                category=IntentCategory.INFORMATION,
                domain=BusinessDomain.CROSS_INDUSTRY,
                process="GENERAL_DISCOVERY",
                taxonomy_node_id=node_id,
                confidence_boost=0.02,
                aliases=["GENERAL_INQUIRY", "INFORMATION_REQUEST"],
            )
        return None


class CoreClassificationRulePack(AbstractClassificationRulePack):
    """
    Core cross-industry rule pack.
    """

    def __init__(self, version: str = "1.0.0"):
        super().__init__(
            pack_name="CoreClassificationRulePack",
            version=version,
            description="Standard cross-industry deterministic intent classification rules.",
        )
        self._rules: List[AbstractClassificationRule] = [
            PricingInquiryClassificationRule(rule_version=version),
            BudgetDiscussionClassificationRule(rule_version=version),
            BookingInterestClassificationRule(rule_version=version),
            NegotiationClassificationRule(rule_version=version),
            ProposalRequestClassificationRule(rule_version=version),
            MeetingRequestClassificationRule(rule_version=version),
            SiteVisitClassificationRule(rule_version=version),
            DocumentRequestClassificationRule(rule_version=version),
            SupportRequestClassificationRule(rule_version=version),
            ComplaintClassificationRule(rule_version=version),
            ReferralClassificationRule(rule_version=version),
            GeneralInquiryClassificationRule(rule_version=version),
        ]

    def get_rules(self) -> List[AbstractClassificationRule]:
        return list(self._rules)
