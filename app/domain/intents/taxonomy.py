"""
HunterOS Engage V1 - Intent Taxonomy
Hierarchical classification and categorization for detected business intents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.domain.intents.models import (
    BusinessImportance,
    IntentTaxonomyCategory,
    IntentType,
)


@dataclass(frozen=True)
class IntentTaxonomyNode:
    """Metadata node in the hierarchical intent taxonomy."""
    intent_type: IntentType
    category: IntentTaxonomyCategory
    display_name: str
    description: str
    taxonomy_path: str
    default_importance: BusinessImportance
    keywords: Tuple[str, ...] = ()
    is_commercial: bool = False
    is_actionable: bool = True


class IntentTaxonomy:
    """
    Central taxonomy definition mapping all 20 Intent Types to categories,
    taxonomy paths, and descriptive business importance.
    """

    _TAXONOMY_MAP: Dict[IntentType, IntentTaxonomyNode] = {
        # ── 1. Commercial ───────────────────────────────────────────────────────
        IntentType.PROPERTY_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.PROPERTY_INQUIRY,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Property Inquiry",
            description="Explicit inquiry regarding real estate properties, units, projects, or locations.",
            taxonomy_path="commercial/property_inquiry",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("property", "flat", "apartment", "villa", "unit", "plot", "tower", "bhk", "layout", "sqft"),
            is_commercial=True,
        ),
        IntentType.PRODUCT_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.PRODUCT_INQUIRY,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Product Inquiry",
            description="Inquiry regarding products, offerings, inventory specifications, or models.",
            taxonomy_path="commercial/product_inquiry",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("product", "feature", "specification", "version", "offering", "catalog"),
            is_commercial=True,
        ),
        IntentType.PRICING_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.PRICING_INQUIRY,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Pricing Inquiry",
            description="Explicit request for pricing, cost breakdown, quotation, or rate list.",
            taxonomy_path="commercial/pricing_inquiry",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("price", "cost", "pricing", "quote", "quotation", "rate", "rate card", "how much", "charges"),
            is_commercial=True,
        ),
        IntentType.BUDGET_DISCUSSION: IntentTaxonomyNode(
            intent_type=IntentType.BUDGET_DISCUSSION,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Budget Discussion",
            description="Discussion of affordability, budget range, investment limits, or financial parameters.",
            taxonomy_path="commercial/budget_discussion",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("budget", "afford", "crore", "lakh", "range", "cap", "limit", "within my budget", "max budget"),
            is_commercial=True,
        ),
        IntentType.BOOKING_INTEREST: IntentTaxonomyNode(
            intent_type=IntentType.BOOKING_INTEREST,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Booking Interest",
            description="Customer expression of intent to reserve, book, or put down token amount.",
            taxonomy_path="commercial/booking_interest",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("book", "booking", "reserve", "token", "advance payment", "hold unit", "blocking amount", "confirm purchase"),
            is_commercial=True,
        ),
        IntentType.NEGOTIATION: IntentTaxonomyNode(
            intent_type=IntentType.NEGOTIATION,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Negotiation",
            description="Request for discounts, payment terms adjustment, waivers, or best offer negotiations.",
            taxonomy_path="commercial/negotiation",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("discount", "negotiate", "deal", "best price", "special offer", "waiver", "concession", "reduce price"),
            is_commercial=True,
        ),
        IntentType.FINANCE_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.FINANCE_INQUIRY,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Finance Inquiry",
            description="Questions about loans, EMI options, bank approvals, mortgages, or payment plans.",
            taxonomy_path="commercial/finance_inquiry",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("loan", "emi", "bank loan", "mortgage", "interest rate", "payment plan", "installment", "hfc", "financing"),
            is_commercial=True,
        ),
        IntentType.INVESTMENT_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.INVESTMENT_INQUIRY,
            category=IntentTaxonomyCategory.COMMERCIAL,
            display_name="Investment Inquiry",
            description="Inquiries focused on return on investment (ROI), capital appreciation, or rental yields.",
            taxonomy_path="commercial/investment_inquiry",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("investment", "roi", "rental yield", "appreciation", "invest", "returns", "capital growth", "investor"),
            is_commercial=True,
        ),

        # ── 2. Operational ──────────────────────────────────────────────────────
        IntentType.DOCUMENT_REQUEST: IntentTaxonomyNode(
            intent_type=IntentType.DOCUMENT_REQUEST,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Document Request",
            description="Request for brochures, floor plans, legal approvals, NOCs, or documentation.",
            taxonomy_path="operational/document_request",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("brochure", "floor plan", "catalogue", "document", "pdf", "sheet", "legal approval", "noc", "sanction plan"),
        ),
        IntentType.SUPPORT_REQUEST: IntentTaxonomyNode(
            intent_type=IntentType.SUPPORT_REQUEST,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Support Request",
            description="Request for operational assistance, customer service, or guidance.",
            taxonomy_path="operational/support_request",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("help", "support", "assist", "issue", "portal", "account", "service request", "troubleshoot"),
        ),
        IntentType.SCHEDULE_MEETING: IntentTaxonomyNode(
            intent_type=IntentType.SCHEDULE_MEETING,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Schedule Meeting",
            description="Request to schedule a phone call, virtual meeting, or consultation.",
            taxonomy_path="operational/schedule_meeting",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("call me", "schedule call", "meeting", "zoom", "google meet", "discuss over call", "callback"),
        ),
        IntentType.SCHEDULE_SITE_VISIT: IntentTaxonomyNode(
            intent_type=IntentType.SCHEDULE_SITE_VISIT,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Schedule Site Visit",
            description="Request or confirmation to visit physical property site, sample flat, or office.",
            taxonomy_path="operational/schedule_site_visit",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("site visit", "visit site", "come over", "sample flat", "inspection", "tour", "walkthrough", "see property"),
        ),
        IntentType.PROPOSAL_REQUEST: IntentTaxonomyNode(
            intent_type=IntentType.PROPOSAL_REQUEST,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Proposal Request",
            description="Formal request for a written commercial proposal, payment schedule, or agreement draft.",
            taxonomy_path="operational/proposal_request",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("proposal", "formal quote", "agreement draft", "cost sheet", "detailed proposal", "commercial proposal"),
        ),
        IntentType.CANCELLATION: IntentTaxonomyNode(
            intent_type=IntentType.CANCELLATION,
            category=IntentTaxonomyCategory.OPERATIONAL,
            display_name="Cancellation",
            description="Request to cancel an appointment, visit, booking, or subscription.",
            taxonomy_path="operational/cancellation",
            default_importance=BusinessImportance.CRITICAL_COMMUNICATION,
            keywords=("cancel", "cancellation", "abort", "call off", "withdraw", "refund", "not interested anymore", "opt out"),
        ),

        # ── 3. Relationship ─────────────────────────────────────────────────────
        IntentType.REFERRAL: IntentTaxonomyNode(
            intent_type=IntentType.REFERRAL,
            category=IntentTaxonomyCategory.RELATIONSHIP,
            display_name="Referral",
            description="Customer referring a colleague, family member, friend, or external party.",
            taxonomy_path="relationship/referral",
            default_importance=BusinessImportance.COMMERCIAL,
            keywords=("refer", "referral", "friend", "colleague", "brother", "relative", "someone looking for", "recommended by"),
        ),
        IntentType.PARTNERSHIP_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.PARTNERSHIP_INQUIRY,
            category=IntentTaxonomyCategory.RELATIONSHIP,
            display_name="Partnership Inquiry",
            description="Channel partner, real estate agent, broker, vendor, or B2B collaboration inquiry.",
            taxonomy_path="relationship/partnership_inquiry",
            default_importance=BusinessImportance.OPERATIONAL,
            keywords=("partner", "partnership", "channel partner", "broker", "collaborate", "vendor", "agency", "tie up"),
        ),
        IntentType.COMPLAINT: IntentTaxonomyNode(
            intent_type=IntentType.COMPLAINT,
            category=IntentTaxonomyCategory.RELATIONSHIP,
            display_name="Complaint",
            description="Customer expressing dissatisfaction, grievance, unmet commitments, or delay escalation.",
            taxonomy_path="relationship/complaint",
            default_importance=BusinessImportance.CRITICAL_COMMUNICATION,
            keywords=("complaint", "dissatisfied", "unacceptable", "delay", "poor service", "escalate", "frustrated", "bad experience"),
        ),

        # ── 4. Information ──────────────────────────────────────────────────────
        IntentType.INFORMATION_REQUEST: IntentTaxonomyNode(
            intent_type=IntentType.INFORMATION_REQUEST,
            category=IntentTaxonomyCategory.INFORMATION,
            display_name="Information Request",
            description="General inquiry seeking facts, details, policies, timelines, or specifications.",
            taxonomy_path="information/information_request",
            default_importance=BusinessImportance.INFORMATIONAL,
            keywords=("information", "details", "how does", "tell me about", "what is", "where is", "policy", "possession date"),
        ),
        IntentType.GENERAL_INQUIRY: IntentTaxonomyNode(
            intent_type=IntentType.GENERAL_INQUIRY,
            category=IntentTaxonomyCategory.INFORMATION,
            display_name="General Inquiry",
            description="Generic or introductory message exploring options without specific commercial scope.",
            taxonomy_path="information/general_inquiry",
            default_importance=BusinessImportance.INFORMATIONAL,
            keywords=("hi", "hello", "inquiry", "looking for options", "interested in knowing more", "general"),
        ),

        # ── 5. Custom ───────────────────────────────────────────────────────────
        IntentType.CUSTOM_INTENT: IntentTaxonomyNode(
            intent_type=IntentType.CUSTOM_INTENT,
            category=IntentTaxonomyCategory.CUSTOM,
            display_name="Custom Intent",
            description="Extensible custom enterprise intent registered by domain plugins.",
            taxonomy_path="custom/custom_intent",
            default_importance=BusinessImportance.INFORMATIONAL,
            keywords=(),
        ),
    }

    @classmethod
    def get_node(cls, intent_type: IntentType) -> IntentTaxonomyNode:
        """Retrieve taxonomy metadata for an intent type."""
        return cls._TAXONOMY_MAP.get(
            intent_type,
            cls._TAXONOMY_MAP[IntentType.GENERAL_INQUIRY],
        )

    @classmethod
    def get_category(cls, intent_type: IntentType) -> IntentTaxonomyCategory:
        return cls.get_node(intent_type).category

    @classmethod
    def get_taxonomy_path(cls, intent_type: IntentType) -> str:
        return cls.get_node(intent_type).taxonomy_path

    @classmethod
    def get_default_importance(cls, intent_type: IntentType) -> BusinessImportance:
        return cls.get_node(intent_type).default_importance

    @classmethod
    def get_types_by_category(cls, category: IntentTaxonomyCategory) -> List[IntentType]:
        return [
            node.intent_type
            for node in cls._TAXONOMY_MAP.values()
            if node.category == category
        ]

    @classmethod
    def get_all_nodes(cls) -> List[IntentTaxonomyNode]:
        return list(cls._TAXONOMY_MAP.values())

    @classmethod
    def get_taxonomy_tree(cls) -> Dict[str, Any]:
        """Generate structured hierarchical taxonomy tree grouped by Category."""
        tree: Dict[str, Any] = {}
        for node in cls._TAXONOMY_MAP.values():
            cat = node.category.value
            if cat not in tree:
                tree[cat] = []
            tree[cat].append({
                "intent_type": node.intent_type.value,
                "display_name": node.display_name,
                "description": node.description,
                "taxonomy_path": node.taxonomy_path,
                "default_importance": node.default_importance.value,
                "is_commercial": node.is_commercial,
                "is_actionable": node.is_actionable,
            })
        return tree


# Alias for concise referencing
TaxonomyNode = IntentTaxonomyNode
