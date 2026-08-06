"""
HunterOS Engage V1 - Intent Relationship Rules
Modular rules for inferring structural and contextual intent relationships.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Set, Tuple
import uuid

from app.domain.intents.classification.models import (
    IntentCategory,
    IntentRelationship,
    IntentRelationshipType,
)

if TYPE_CHECKING:
    from app.domain.intents.classification.context import IntentClassificationContext


class AbstractRelationshipRule(ABC):
    """Abstract base class for intent relationship evaluation rules."""

    def __init__(self, rule_name: str, rule_version: str = "1.0.0", description: str = ""):
        self.rule_name = rule_name
        self.rule_version = rule_version
        self.description = description

    @abstractmethod
    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        """Evaluate relationship conditions across classified intents."""
        pass


class DependencyRule(AbstractRelationshipRule):
    """
    Infers operational or commercial dependencies between intents.
    Example: Site Visit or Meeting Request depends on Property Inquiry.
    """

    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="StandardDependencyRule",
            rule_version=rule_version,
            description="Identifies prerequisite dependencies between operational/commercial intents.",
        )

    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        intents = context.classified_intents
        if len(intents) < 2:
            return relationships

        # Find inquiries and visits
        inquiries = [
            i for i in intents
            if "property_inquiry" in i.taxonomy_path.lower() or "product_inquiry" in i.taxonomy_path.lower()
        ]
        visits_or_meetings = [
            i for i in intents
            if "site_visit" in i.taxonomy_path.lower() or "meeting_request" in i.taxonomy_path.lower()
        ]
        proposals = [
            i for i in intents
            if "proposal_request" in i.taxonomy_path.lower() or "quote_request" in i.taxonomy_path.lower()
        ]
        budgets_or_prices = [
            i for i in intents
            if "pricing_inquiry" in i.taxonomy_path.lower() or "budget_discussion" in i.taxonomy_path.lower()
        ]

        # Rule 1: Site visits depend on Property Inquiries
        for visit in visits_or_meetings:
            for inq in inquiries:
                if visit.classified_intent_id != inq.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=visit.classified_intent_id,
                            target_intent_id=inq.classified_intent_id,
                            relationship_type=IntentRelationshipType.DEPENDENT_INTENT,
                            reason=f"Operational engagement '{visit.taxonomy_path}' is dependent on prerequisite '{inq.taxonomy_path}'.",
                            confidence=0.90,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        # Rule 2: Proposal requests depend on Pricing/Budget discussion
        for prop in proposals:
            for bp in budgets_or_prices:
                if prop.classified_intent_id != bp.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=prop.classified_intent_id,
                            target_intent_id=bp.classified_intent_id,
                            relationship_type=IntentRelationshipType.DEPENDENT_INTENT,
                            reason=f"Proposal fulfillment '{prop.taxonomy_path}' depends on pricing clarification '{bp.taxonomy_path}'.",
                            confidence=0.88,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        # Rule 3: Booking commitment depends on Pricing/Budget discussion
        bookings = [
            i for i in intents
            if "booking_interest" in i.taxonomy_path.lower()
        ]
        for b in bookings:
            for bp in budgets_or_prices:
                if b.classified_intent_id != bp.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=b.classified_intent_id,
                            target_intent_id=bp.classified_intent_id,
                            relationship_type=IntentRelationshipType.DEPENDENT_INTENT,
                            reason=f"Booking commitment '{b.taxonomy_path}' depends on pricing clarification '{bp.taxonomy_path}'.",
                            confidence=0.90,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        return relationships


class ConflictRule(AbstractRelationshipRule):
    """
    Identifies conflicting or mutually opposing intents in a conversation.
    Example: Booking Interest vs Cancellation or Severe Complaint.
    """

    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="StandardConflictRule",
            rule_version=rule_version,
            description="Identifies opposing intents such as booking intent versus cancellation.",
        )

    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        intents = context.classified_intents
        if len(intents) < 2:
            return relationships

        bookings = [
            i for i in intents
            if "booking_interest" in i.taxonomy_path.lower()
        ]
        cancellations = [
            i for i in intents
            if "cancellation" in i.taxonomy_path.lower()
        ]
        complaints = [
            i for i in intents
            if "complaint" in i.taxonomy_path.lower()
        ]

        # Booking vs Cancellation
        for b in bookings:
            for c in cancellations:
                relationships.append(
                    IntentRelationship(
                        source_intent_id=b.classified_intent_id,
                        target_intent_id=c.classified_intent_id,
                        relationship_type=IntentRelationshipType.CONFLICTING_INTENT,
                        reason=f"High purchase intent '{b.taxonomy_path}' conflicts with withdrawal '{c.taxonomy_path}'.",
                        confidence=0.95,
                        metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                    )
                )

        # Booking vs Complaint
        for b in bookings:
            for cp in complaints:
                relationships.append(
                    IntentRelationship(
                        source_intent_id=b.classified_intent_id,
                        target_intent_id=cp.classified_intent_id,
                        relationship_type=IntentRelationshipType.CONFLICTING_INTENT,
                        reason=f"Purchase intent '{b.taxonomy_path}' has friction with customer complaint '{cp.taxonomy_path}'.",
                        confidence=0.85,
                        metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                    )
                )

        return relationships


class ComplementRule(AbstractRelationshipRule):
    """
    Identifies complementary or mutually reinforcing intents.
    Example: Budget Discussion complements Pricing Inquiry; Document Request complements Site Visit.
    """

    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="StandardComplementRule",
            rule_version=rule_version,
            description="Identifies complementary and reinforcing intents across commercial and operational categories.",
        )

    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        intents = context.classified_intents
        if len(intents) < 2:
            return relationships

        # 1. Budget Discussion + Pricing Inquiry
        budgets = [i for i in intents if "budget_discussion" in i.taxonomy_path.lower()]
        prices = [i for i in intents if "pricing_inquiry" in i.taxonomy_path.lower()]
        for b in budgets:
            for p in prices:
                if b.classified_intent_id != p.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=b.classified_intent_id,
                            target_intent_id=p.classified_intent_id,
                            relationship_type=IntentRelationshipType.COMPLEMENTARY_INTENT,
                            reason=f"Budget discussion '{b.taxonomy_path}' complements pricing inquiry '{p.taxonomy_path}'.",
                            confidence=0.92,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        # 2. Document Request + Site Visit / Meeting
        docs = [i for i in intents if "document_request" in i.taxonomy_path.lower()]
        ops = [i for i in intents if "site_visit" in i.taxonomy_path.lower() or "meeting_request" in i.taxonomy_path.lower()]
        for d in docs:
            for o in ops:
                if d.classified_intent_id != o.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=d.classified_intent_id,
                            target_intent_id=o.classified_intent_id,
                            relationship_type=IntentRelationshipType.COMPLEMENTARY_INTENT,
                            reason=f"Document request '{d.taxonomy_path}' complements scheduling '{o.taxonomy_path}'.",
                            confidence=0.88,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        return relationships


class HierarchyRule(AbstractRelationshipRule):
    """
    Identifies parent-child intent relationships (e.g. general inquiry as parent of specific inquiry).
    """

    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="StandardHierarchyRule",
            rule_version=rule_version,
            description="Identifies parent-child structural relationships between broad and specific intents.",
        )

    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        intents = context.classified_intents
        if len(intents) < 2:
            return relationships

        general_inquiries = [i for i in intents if "general_inquiry" in i.taxonomy_path.lower()]
        specific_intents = [
            i for i in intents
            if i.business_category in (IntentCategory.COMMERCIAL, IntentCategory.OPERATIONAL)
        ]

        for gen in general_inquiries:
            for spec in specific_intents:
                if gen.classified_intent_id != spec.classified_intent_id:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=gen.classified_intent_id,
                            target_intent_id=spec.classified_intent_id,
                            relationship_type=IntentRelationshipType.PARENT_INTENT,
                            reason=f"General conversational inquiry '{gen.taxonomy_path}' acts as umbrella parent for '{spec.taxonomy_path}'.",
                            confidence=0.80,
                            metadata={"rule": self.rule_name, "rule_version": self.rule_version},
                        )
                    )

        return relationships


class RelatedRule(AbstractRelationshipRule):
    """
    Identifies general relatedness between intents sharing the same category or message references.
    """

    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="StandardRelatedRule",
            rule_version=rule_version,
            description="Links related intents that share category or overlapping evidence messages.",
        )

    def evaluate(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        intents = context.classified_intents
        if len(intents) < 2:
            return relationships

        seen_pairs: Set[Tuple[uuid.UUID, uuid.UUID]] = set()

        for i, first in enumerate(intents):
            for second in intents[i + 1:]:
                if first.classified_intent_id == second.classified_intent_id:
                    continue

                # Check shared evidence messages
                shared_messages = set(first.supporting_evidence.source_message_ids) & set(
                    second.supporting_evidence.source_message_ids
                )
                if shared_messages and (first.classified_intent_id, second.classified_intent_id) not in seen_pairs:
                    seen_pairs.add((first.classified_intent_id, second.classified_intent_id))
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=first.classified_intent_id,
                            target_intent_id=second.classified_intent_id,
                            relationship_type=IntentRelationshipType.RELATED_INTENT,
                            reason=f"Intents share {len(shared_messages)} overlapping evidence message(s).",
                            confidence=0.85,
                            metadata={"shared_messages": list(shared_messages), "rule": self.rule_name},
                        )
                    )

        return relationships


# Aliases for consistent naming convention
DependencyRelationshipRule = DependencyRule
ConflictRelationshipRule = ConflictRule
ComplementRelationshipRule = ComplementRule
HierarchyRelationshipRule = HierarchyRule
RelatedRelationshipRule = RelatedRule
