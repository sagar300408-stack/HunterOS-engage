"""
HunterOS Engage — Hierarchical Topic Taxonomy (Phase 2.2.1)

Defines a structured, deterministic topic taxonomy hierarchy allowing
path-based topic classification (e.g., 'sales/pricing/discount').
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TopicTaxonomyNode:
    """A node in the hierarchical topic taxonomy tree."""

    name: str
    path: str  # e.g., 'sales/pricing/discount'
    category: str  # Top-level category
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    children: Dict[str, TopicTaxonomyNode] = field(default_factory=dict)
    parent_path: Optional[str] = None
    description: Optional[str] = None
    weight: float = 1.0

    def add_child(self, child: TopicTaxonomyNode) -> None:
        """Attach a sub-topic node."""
        child.parent_path = self.path
        slug = child.path.split("/")[-1].lower()
        self.children[slug] = child
        self.children[child.name.lower()] = child

    def match(self, text: str) -> Tuple[int, float]:
        """
        Evaluate keyword and regex pattern matches in the text.
        Returns: (match_count, confidence_score)
        """
        lowered = text.lower()
        count = 0

        # Exact keyword matches
        for kw in self.keywords:
            kw_low = kw.lower()
            if kw_low in lowered:
                # Count occurrences using word boundaries if single word
                if " " not in kw_low:
                    matches = len(re.findall(rf"\b{re.escape(kw_low)}\b", lowered))
                else:
                    matches = lowered.count(kw_low)
                count += max(1, matches)

        # Regex pattern matches
        for pat in self.patterns:
            try:
                matches = len(re.findall(pat, text, flags=re.IGNORECASE))
                count += matches
            except re.error:
                continue

        if count == 0:
            return 0, 0.0

        # Confidence is bounded and scaled with occurrence count
        confidence = min(1.0, 0.5 + (0.1 * min(count, 5)))
        return count, confidence


class TopicTaxonomy:
    """
    Hierarchical topic taxonomy tree holding business categories and sub-topics.
    Supports extensible path-based lookup and deterministic text classification.
    """

    def __init__(self) -> None:
        self.roots: Dict[str, TopicTaxonomyNode] = {}
        self._build_default_hierarchy()

    def _build_default_hierarchy(self) -> None:
        """Populate built-in enterprise topic taxonomies."""
        # 1. Sales & Commercial
        sales = TopicTaxonomyNode(name="Sales", path="sales", category="Sales", description="Commercial and sales discussions")
        pricing = TopicTaxonomyNode(name="Pricing", path="sales/pricing", category="Sales", keywords=["price", "cost", "quote", "rate", "tariff", "fee"])
        discount = TopicTaxonomyNode(name="Discount", path="sales/pricing/discount", category="Sales", keywords=["discount", "offer", "concession", "deal", "promo", "rebate", "bargain"])
        payment = TopicTaxonomyNode(name="Payment", path="sales/pricing/payment", category="Sales", keywords=["payment", "installment", "downpayment", "invoice", "emi", "bank transfer", "cheque", "card"])
        pricing.add_child(discount)
        pricing.add_child(payment)
        sales.add_child(pricing)

        contracts = TopicTaxonomyNode(name="Contract", path="sales/contract", category="Sales", keywords=["contract", "agreement", "nda", "terms", "sla", "sign", "clause", "mou"])
        sales.add_child(contracts)
        self.roots["sales"] = sales

        # 2. Real Estate / Property
        real_estate = TopicTaxonomyNode(name="Real Estate", path="real_estate", category="Real Estate", description="Property, location, and housing specifications")
        prop = TopicTaxonomyNode(name="Property", path="real_estate/property", category="Real Estate", keywords=["property", "apartment", "flat", "villa", "penthouse", "sqft", "sq ft", "bhk", "bedroom", "floor plan", "plot", "residence", "commercial space", "office"])
        loc = TopicTaxonomyNode(name="Location", path="real_estate/location", category="Real Estate", keywords=["location", "neighborhood", "city", "metro", "address", "connectivity", "sector", "road", "distance", "amenities", "view"])
        budget = TopicTaxonomyNode(name="Budget", path="real_estate/budget", category="Real Estate", keywords=["budget", "lakh", "crore", "cr", "afford", "investment", "price range", "valuation"])
        real_estate.add_child(prop)
        real_estate.add_child(loc)
        real_estate.add_child(budget)
        self.roots["real_estate"] = real_estate

        # 3. Product & Technology
        product = TopicTaxonomyNode(name="Product", path="product", category="Product", description="Product specifications and features")
        features = TopicTaxonomyNode(name="Features", path="product/features", category="Product", keywords=["feature", "integration", "api", "dashboard", "export", "webhook", "ai", "automation", "sync", "mobile app", "workflow"])
        technical = TopicTaxonomyNode(name="Technical", path="product/technical", category="Product", keywords=["technical", "architecture", "database", "latency", "uptime", "security", "hosting", "cloud", "aws", "encryption", "performance"])
        product.add_child(features)
        product.add_child(technical)
        self.roots["product"] = product

        # 4. Scheduling & Appointments
        scheduling = TopicTaxonomyNode(name="Scheduling", path="scheduling", category="Scheduling", description="Meetings, site visits, and time coordination")
        meeting = TopicTaxonomyNode(name="Meeting", path="scheduling/meeting", category="Scheduling", keywords=["meeting", "call", "zoom", "site visit", "appointment", "schedule", "calendar", "demo", "viewing", "tour"])
        followup = TopicTaxonomyNode(name="Follow-Up", path="scheduling/follow_up", category="Scheduling", keywords=["follow up", "follow-up", "next week", "tomorrow", "check in", "reminder", "callback", "later"])
        scheduling.add_child(meeting)
        scheduling.add_child(followup)
        self.roots["scheduling"] = scheduling

        # 5. Customer Support & Operations
        support = TopicTaxonomyNode(name="Support", path="support", category="Support", description="Support inquiries, assistance, and resolutions")
        inquiry = TopicTaxonomyNode(name="Inquiry", path="support/inquiry", category="Support", keywords=["help", "question", "inquiry", "how to", "information", "details", "brochure", "guidance"])
        issue = TopicTaxonomyNode(name="Issue", path="support/issue", category="Support", keywords=["issue", "problem", "error", "bug", "broken", "complaint", "delay", "failed", "unhappy"])
        support.add_child(inquiry)
        support.add_child(issue)
        self.roots["support"] = support

    def register_node(self, node: TopicTaxonomyNode) -> None:
        """Register or override a custom taxonomy node in the tree."""
        parts = node.path.split("/")
        if len(parts) == 1:
            self.roots[parts[0]] = node
            return

        # Traverse to parent
        parent = self.get_node("/".join(parts[:-1]))
        if parent:
            parent.add_child(node)
        else:
            # Fallback root
            self.roots[parts[0]] = node

    def get_node(self, path: str) -> Optional[TopicTaxonomyNode]:
        """Find node by path (e.g., 'sales/pricing/discount')."""
        parts = path.strip("/").split("/")
        if not parts:
            return None

        root_key = parts[0].lower()
        curr = None
        for k, v in self.roots.items():
            if k.lower() == root_key or v.name.lower() == root_key or v.path.lower() == root_key:
                curr = v
                break
        if not curr:
            return None

        for part in parts[1:]:
            part_low = part.lower().replace("-", "_").replace(" ", "_")
            found = False
            for child_key, child_node in curr.children.items():
                child_slug = child_node.path.split("/")[-1].lower().replace("-", "_").replace(" ", "_")
                child_name_slug = child_node.name.lower().replace("-", "_").replace(" ", "_")
                key_slug = child_key.lower().replace("-", "_").replace(" ", "_")
                if part_low in (child_slug, child_name_slug, key_slug):
                    curr = child_node
                    found = True
                    break
            if not found:
                return None
        return curr

    def collect_all_nodes(self) -> List[TopicTaxonomyNode]:
        """Collect flattened list of all nodes across all depths."""
        nodes: List[TopicTaxonomyNode] = []

        def _traverse(node: TopicTaxonomyNode) -> None:
            nodes.append(node)
            for child in node.children.values():
                _traverse(child)

        for root in self.roots.values():
            _traverse(root)
        return nodes

    def match_all(self, text: str) -> List[Tuple[TopicTaxonomyNode, int, float]]:
        """
        Evaluate text against all taxonomy nodes.
        Returns list of (node, match_count, confidence) sorted by match count and path depth.
        """
        matches: List[Tuple[TopicTaxonomyNode, int, float]] = []
        for node in self.collect_all_nodes():
            count, conf = node.match(text)
            if count > 0:
                matches.append((node, count, conf))

        # Sort: higher match count first, then deeper taxonomy path
        matches.sort(key=lambda x: (x[1], len(x[0].path.split("/"))), reverse=True)
        return matches


# Global default taxonomy instance
default_topic_taxonomy = TopicTaxonomy()
