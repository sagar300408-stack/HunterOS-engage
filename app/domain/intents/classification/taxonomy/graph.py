"""
HunterOS Engage V1 - Business Intent Taxonomy Graph
Thread-safe Directed Acyclic Graph (DAG) taxonomy supporting multi-parent paths and cross-category links.
"""

from __future__ import annotations

from collections import defaultdict, deque
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
    TaxonomyPath,
)


class BusinessIntentTaxonomyGraph:
    """
    Graph-based taxonomy engine for classifying intents.
    Supports nodes with multiple parent categories, cross-category links, and multi-path queries.
    """

    def __init__(self, version: str = "2.3.2"):
        self._version = version
        self._lock = threading.RLock()
        self._nodes: Dict[str, TaxonomyNode] = {}
        self._outgoing: Dict[str, Set[str]] = defaultdict(set)
        self._incoming: Dict[str, Set[str]] = defaultdict(set)
        self._edges: List[TaxonomyEdge] = []
        self._initialize_default_graph()

    @property
    def version(self) -> str:
        return self._version

    def add_node(self, node: TaxonomyNode) -> None:
        """Register a taxonomy node in the graph."""
        with self._lock:
            self._nodes[node.node_id] = node

    def add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation: str = "PARENT_OF",
        weight: float = 1.0,
        check_cycle: bool = True,
    ) -> None:
        """Add directed edge between taxonomy nodes."""
        with self._lock:
            if source_node_id not in self._nodes:
                raise KeyError(f"Source taxonomy node '{source_node_id}' does not exist.")
            if target_node_id not in self._nodes:
                raise KeyError(f"Target taxonomy node '{target_node_id}' does not exist.")

            edge = TaxonomyEdge(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                relation=relation,
                weight=weight,
            )
            self._edges.append(edge)
            self._outgoing[source_node_id].add(target_node_id)
            self._incoming[target_node_id].add(source_node_id)

            if check_cycle and self.has_cycle():
                self._edges.pop()
                self._outgoing[source_node_id].remove(target_node_id)
                self._incoming[target_node_id].remove(source_node_id)
                raise ValueError(f"Adding edge '{source_node_id}' -> '{target_node_id}' creates a cycle in taxonomy graph.")

    def get_node(self, node_id: str) -> Optional[TaxonomyNode]:
        """Look up a taxonomy node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_root_nodes(self) -> List[TaxonomyNode]:
        """Returns all nodes in the graph that have no incoming parent edges."""
        with self._lock:
            return [
                node for node_id, node in self._nodes.items()
                if not self._incoming.get(node_id)
            ]

    def get_parents(self, node_id: str) -> List[TaxonomyNode]:
        """Get direct parent nodes of a given node."""
        with self._lock:
            parent_ids = self._incoming.get(node_id, set())
            return [self._nodes[pid] for pid in parent_ids if pid in self._nodes]

    def get_children(self, node_id: str) -> List[TaxonomyNode]:
        """Get direct children nodes of a given node."""
        with self._lock:
            child_ids = self._outgoing.get(node_id, set())
            return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Traverse upwards to return all ancestor node IDs."""
        with self._lock:
            ancestors: Set[str] = set()
            queue = deque([node_id])
            while queue:
                curr = queue.popleft()
                for p in self._incoming.get(curr, set()):
                    if p not in ancestors:
                        ancestors.add(p)
                        queue.append(p)
            return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """Traverse downwards to return all descendant node IDs."""
        with self._lock:
            descendants: Set[str] = set()
            queue = deque([node_id])
            while queue:
                curr = queue.popleft()
                for c in self._outgoing.get(curr, set()):
                    if c not in descendants:
                        descendants.add(c)
                        queue.append(c)
            return descendants

    def get_all_paths_to_root(self, node_id: str) -> List[TaxonomyPath]:
        """
        Find all paths from any root node down to the specified node.
        Handles multi-parent taxonomy nodes.
        """
        with self._lock:
            if node_id not in self._nodes:
                return []

            results: List[List[str]] = []

            def _dfs(curr_id: str, current_path: List[str], visited: Set[str]):
                if curr_id in visited:
                    return  # Guard against cycles
                visited.add(curr_id)
                parents = self._incoming.get(curr_id, set())
                if not parents:
                    # Root reached
                    results.append(list(reversed(current_path)))
                else:
                    for p in parents:
                        _dfs(p, current_path + [p], set(visited))

            _dfs(node_id, [node_id], set())
            return [TaxonomyPath.from_nodes(path) for path in results]

    def find_primary_path(self, node_id: str) -> str:
        """Returns the canonical primary path string for a node (e.g. 'commercial/pricing_inquiry')."""
        paths = self.get_all_paths_to_root(node_id)
        if not paths:
            return node_id
        # Primary is shortest root-to-leaf path or first discovered
        return paths[0].path_str

    def has_cycle(self) -> bool:
        """Detects if any cycles exist in the taxonomy graph."""
        with self._lock:
            visited = set()
            rec_stack = set()

            def _is_cyclic(node_id: str) -> bool:
                visited.add(node_id)
                rec_stack.add(node_id)
                for neighbor in self._outgoing.get(node_id, set()):
                    if neighbor not in visited:
                        if _is_cyclic(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                rec_stack.remove(node_id)
                return False

            for n_id in self._nodes:
                if n_id not in visited:
                    if _is_cyclic(n_id):
                        return True
            return False

    def list_nodes_by_category(self, category: IntentCategory) -> List[TaxonomyNode]:
        """Filter nodes by business category."""
        with self._lock:
            return [n for n in self._nodes.values() if n.category == category]

    def list_nodes_by_domain(self, domain: BusinessDomain) -> List[TaxonomyNode]:
        """Filter nodes by business domain."""
        with self._lock:
            return [n for n in self._nodes.values() if n.business_domain in (domain, BusinessDomain.CROSS_INDUSTRY)]

    def export_graph(self) -> Dict[str, Any]:
        """Exports graph topology for UI and external consumers."""
        with self._lock:
            return {
                "version": self._version,
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in self._edges],
            }

    # ── Default Graph Initialization ─────────────────────────────────────────

    def _initialize_default_graph(self) -> None:
        """Seed the graph with cross-industry taxonomy structure."""
        roots = [
            TaxonomyNode(
                node_id="commercial",
                category=IntentCategory.COMMERCIAL,
                display_name="Commercial Intent",
                description="Financial, transaction, and commercial procurement interests.",
                default_process="SALES_QUALIFICATION",
            ),
            TaxonomyNode(
                node_id="operational",
                category=IntentCategory.OPERATIONAL,
                display_name="Operational Intent",
                description="Scheduling, documentation, logistics, and service execution.",
                default_process="APPOINTMENT_SCHEDULING",
            ),
            TaxonomyNode(
                node_id="relationship",
                category=IntentCategory.RELATIONSHIP,
                display_name="Relationship Intent",
                description="Customer relationship, partnership, complaints, and referrals.",
                default_process="RETENTION_RELATIONSHIP",
            ),
            TaxonomyNode(
                node_id="information",
                category=IntentCategory.INFORMATION,
                display_name="Information Intent",
                description="Product inquiries, property searches, and informational discovery.",
                default_process="GENERAL_DISCOVERY",
            ),
            TaxonomyNode(
                node_id="custom",
                category=IntentCategory.CUSTOM,
                display_name="Custom Intent",
                description="Extensible custom business classification.",
                default_process="GENERAL_DISCOVERY",
            ),
        ]
        for r in roots:
            self.add_node(r)

        # Commercial Subtree
        commercial_nodes = [
            TaxonomyNode(
                node_id="commercial.pricing_inquiry",
                category=IntentCategory.COMMERCIAL,
                display_name="Pricing Inquiry",
                description="Customer asking for pricing, rate lists, or discounts.",
                default_process="SALES_QUALIFICATION",
                aliases=["PRICING_INQUIRY", "PRICE_REQUEST", "COST_INQUIRY"],
            ),
            TaxonomyNode(
                node_id="commercial.budget_discussion",
                category=IntentCategory.COMMERCIAL,
                display_name="Budget Discussion",
                description="Discussion of affordability, price bounds, and financial parameters.",
                default_process="SALES_QUALIFICATION",
                aliases=["BUDGET_DISCUSSION", "FINANCIAL_BOUNDS"],
            ),
            TaxonomyNode(
                node_id="commercial.booking_interest",
                category=IntentCategory.COMMERCIAL,
                display_name="Booking Interest",
                description="High purchase intent, block unit, or place booking deposit.",
                default_process="DEAL_CLOSING",
                aliases=["BOOKING_INTEREST", "PURCHASE_INTENT", "COMMITMENT"],
            ),
            TaxonomyNode(
                node_id="commercial.negotiation",
                category=IntentCategory.COMMERCIAL,
                display_name="Negotiation",
                description="Discussions regarding terms, pricing flexibility, or payment plans.",
                default_process="DEAL_CLOSING",
                aliases=["NEGOTIATION", "COMMERCIAL_TERMS"],
            ),
            TaxonomyNode(
                node_id="commercial.negotiation.discount_discussion",
                category=IntentCategory.COMMERCIAL,
                display_name="Discount Discussion",
                description="Specific requests for price reduction or special offers.",
                default_process="DEAL_CLOSING",
                aliases=["DISCOUNT_DISCUSSION", "REBATE_REQUEST"],
            ),
            TaxonomyNode(
                node_id="commercial.proposal_request",
                category=IntentCategory.COMMERCIAL,
                display_name="Proposal Request",
                description="Formal request for quote, quotation, or financial breakdown.",
                default_process="SALES_QUALIFICATION",
                aliases=["PROPOSAL_REQUEST", "QUOTE_REQUEST"],
            ),
            TaxonomyNode(
                node_id="commercial.payment_terms",
                category=IntentCategory.COMMERCIAL,
                display_name="Payment Terms",
                description="Installment schedules, financing, and payment structures.",
                default_process="DEAL_CLOSING",
                aliases=["PAYMENT_TERMS", "PAYMENT_SCHEDULE"],
            ),
        ]
        for cn in commercial_nodes:
            self.add_node(cn)

        # Operational Subtree
        operational_nodes = [
            TaxonomyNode(
                node_id="operational.meeting_request",
                category=IntentCategory.OPERATIONAL,
                display_name="Meeting Request",
                description="Consultation call, discovery session, or virtual meeting.",
                default_process="APPOINTMENT_SCHEDULING",
                aliases=["SCHEDULE_MEETING", "MEETING_REQUEST", "CALL_REQUEST"],
            ),
            TaxonomyNode(
                node_id="operational.site_visit",
                category=IntentCategory.OPERATIONAL,
                display_name="Site Visit",
                description="Physical or in-person property/facility walkthrough.",
                default_process="APPOINTMENT_SCHEDULING",
                aliases=["SCHEDULE_SITE_VISIT", "SITE_VISIT", "TOUR_REQUEST"],
            ),
            TaxonomyNode(
                node_id="operational.document_request",
                category=IntentCategory.OPERATIONAL,
                display_name="Document Request",
                description="Requests for brochures, floor plans, PDFs, and contracts.",
                default_process="DOCUMENT_FULFILLMENT",
                aliases=["DOCUMENT_REQUEST", "BROCHURE_REQUEST", "COLLATERAL_REQUEST"],
            ),
            TaxonomyNode(
                node_id="operational.support_request",
                category=IntentCategory.OPERATIONAL,
                display_name="Support Request",
                description="Customer service assistance, bug report, or helpdesk ticket.",
                default_process="CUSTOMER_SUPPORT",
                aliases=["SUPPORT_REQUEST", "HELP_REQUEST"],
            ),
            TaxonomyNode(
                node_id="operational.cancellation",
                category=IntentCategory.OPERATIONAL,
                display_name="Cancellation",
                description="Cancellation or withdrawal of an appointment or purchase.",
                default_process="RETENTION_RELATIONSHIP",
                aliases=["CANCELLATION", "WITHDRAWAL"],
            ),
            TaxonomyNode(
                node_id="operational.follow_up",
                category=IntentCategory.OPERATIONAL,
                display_name="Follow-up Request",
                description="Requesting later contact or status check-in.",
                default_process="CUSTOMER_SUPPORT",
                aliases=["FOLLOW_UP_REQUEST", "CALLBACK_REQUEST"],
            ),
        ]
        for on in operational_nodes:
            self.add_node(on)

        # Relationship Subtree
        relationship_nodes = [
            TaxonomyNode(
                node_id="relationship.referral",
                category=IntentCategory.RELATIONSHIP,
                display_name="Referral",
                description="Referring friends, colleagues, or associates.",
                default_process="RETENTION_RELATIONSHIP",
                aliases=["REFERRAL", "RECOMMEND_FRIEND"],
            ),
            TaxonomyNode(
                node_id="relationship.partnership",
                category=IntentCategory.RELATIONSHIP,
                display_name="Partnership",
                description="Business partnership or channel partner inquiry.",
                default_process="RETENTION_RELATIONSHIP",
                aliases=["PARTNERSHIP", "CHANNEL_PARTNER"],
            ),
            TaxonomyNode(
                node_id="relationship.existing_customer",
                category=IntentCategory.RELATIONSHIP,
                display_name="Existing Customer",
                description="Interaction from verified previous customer or account holder.",
                default_process="RETENTION_RELATIONSHIP",
                aliases=["EXISTING_CUSTOMER", "ACCOUNT_HOLDER"],
            ),
            TaxonomyNode(
                node_id="relationship.complaint",
                category=IntentCategory.RELATIONSHIP,
                display_name="Complaint",
                description="Customer dissatisfaction, grievance, or escalation.",
                default_process="CUSTOMER_SUPPORT",
                aliases=["COMPLAINT", "GRIEVANCE", "ESCALATION"],
            ),
            TaxonomyNode(
                node_id="relationship.feedback",
                category=IntentCategory.RELATIONSHIP,
                display_name="Customer Feedback",
                description="General commentary or satisfaction feedback.",
                default_process="RETENTION_RELATIONSHIP",
                aliases=["FEEDBACK", "REVIEW"],
            ),
        ]
        for rn in relationship_nodes:
            self.add_node(rn)

        # Information Subtree
        information_nodes = [
            TaxonomyNode(
                node_id="information.product_inquiry",
                category=IntentCategory.INFORMATION,
                display_name="Product Inquiry",
                description="Questions about features, specifications, and offerings.",
                default_process="GENERAL_DISCOVERY",
                aliases=["PRODUCT_INQUIRY", "FEATURE_QUESTION"],
            ),
            TaxonomyNode(
                node_id="information.property_inquiry",
                category=IntentCategory.INFORMATION,
                display_name="Property Inquiry",
                description="Inquiries regarding real estate units, sizes, and amenities.",
                business_domain=BusinessDomain.REAL_ESTATE,
                default_process="LEAD_CAPTURE",
                aliases=["PROPERTY_INQUIRY", "REAL_ESTATE_INQUIRY"],
            ),
            TaxonomyNode(
                node_id="information.finance_inquiry",
                category=IntentCategory.INFORMATION,
                display_name="Finance Inquiry",
                description="Inquiries about loan assistance, EMI, or mortgage eligibility.",
                default_process="SALES_QUALIFICATION",
                aliases=["FINANCE_INQUIRY", "LOAN_INQUIRY"],
            ),
            TaxonomyNode(
                node_id="information.general_inquiry",
                category=IntentCategory.INFORMATION,
                display_name="General Inquiry",
                description="Broad introductory questions and engagement greeting.",
                default_process="GENERAL_DISCOVERY",
                aliases=["GENERAL_INQUIRY", "INFORMATION_REQUEST"],
            ),
            TaxonomyNode(
                node_id="information.location_inquiry",
                category=IntentCategory.INFORMATION,
                display_name="Location Inquiry",
                description="Inquiries about connectivity, neighborhood, and landmarks.",
                default_process="GENERAL_DISCOVERY",
                aliases=["LOCATION_INQUIRY"],
            ),
        ]
        for inf in information_nodes:
            self.add_node(inf)

        # Add Core Edges
        self.add_edge("commercial", "commercial.pricing_inquiry")
        self.add_edge("commercial", "commercial.budget_discussion")
        self.add_edge("commercial", "commercial.booking_interest")
        self.add_edge("commercial", "commercial.negotiation")
        self.add_edge("commercial.negotiation", "commercial.negotiation.discount_discussion")
        # Multi-parent link: Discount discussion is also a child of Pricing Inquiry
        self.add_edge("commercial.pricing_inquiry", "commercial.negotiation.discount_discussion", relation="CROSS_LINK")
        self.add_edge("commercial", "commercial.proposal_request")
        self.add_edge("commercial", "commercial.payment_terms")

        self.add_edge("operational", "operational.meeting_request")
        self.add_edge("operational", "operational.site_visit")
        self.add_edge("operational", "operational.document_request")
        self.add_edge("operational", "operational.support_request")
        self.add_edge("operational", "operational.cancellation")
        self.add_edge("operational", "operational.follow_up")

        self.add_edge("relationship", "relationship.referral")
        self.add_edge("relationship", "relationship.partnership")
        self.add_edge("relationship", "relationship.existing_customer")
        self.add_edge("relationship", "relationship.complaint")
        self.add_edge("relationship", "relationship.feedback")

        self.add_edge("information", "information.product_inquiry")
        self.add_edge("information", "information.property_inquiry")
        self.add_edge("information", "information.finance_inquiry")
        self.add_edge("information", "information.general_inquiry")
        self.add_edge("information", "information.location_inquiry")


default_taxonomy_graph = BusinessIntentTaxonomyGraph()
