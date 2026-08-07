"""
HunterOS Engage V1 - Relationship Resolution Rules
Deterministic rules for identifying parent/child, complementary, supporting, and related intents.
"""

from __future__ import annotations

from typing import List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
)
from app.domain.intents.resolution.rules.base import RelationshipRule


class TaxonomyHierarchyRelationshipRule(RelationshipRule):
    """
    Identifies PARENT and CHILD relationships based on taxonomy path prefixes.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="TaxonomyHierarchyRelationshipRule",
            domain="CROSS_INDUSTRY",
            priority=10,
        )

    def evaluate_relationships(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []

        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if i == j:
                    continue
                parent = nodes[i]
                child = nodes[j]

                # Check taxonomy path prefix
                if parent.taxonomy_path and child.taxonomy_path:
                    if child.taxonomy_path.startswith(parent.taxonomy_path) and child.taxonomy_path != parent.taxonomy_path:
                        relationships.append(
                            IntentRelationship(
                                source_intent_id=parent.intent_id,
                                target_intent_id=child.intent_id,
                                relationship_type=IntentRelationshipType.PARENT,
                                strength=0.95,
                                reason=f"Taxonomy hierarchy: '{parent.taxonomy_path}' is parent prefix of '{child.taxonomy_path}'",
                                rule_name=self.rule_name,
                            )
                        )
                        relationships.append(
                            IntentRelationship(
                                source_intent_id=child.intent_id,
                                target_intent_id=parent.intent_id,
                                relationship_type=IntentRelationshipType.CHILD,
                                strength=0.95,
                                reason=f"Taxonomy hierarchy: '{child.taxonomy_path}' is child of '{parent.taxonomy_path}'",
                                rule_name=self.rule_name,
                            )
                        )
        return relationships


class ComplementaryCommercialRule(RelationshipRule):
    """
    Identifies COMPLEMENTARY relationships between commercial inquiries (e.g., Demo + Pricing).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="ComplementaryCommercialRule",
            domain="CROSS_INDUSTRY",
            priority=20,
        )

    def evaluate_relationships(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        commercial_keywords = {"pricing", "quote", "demo", "trial", "purchase", "features", "discount", "proposal"}

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]

                is_c1 = n1.category == "COMMERCIAL" or any(k in n1.canonical_name.lower() for k in commercial_keywords)
                is_c2 = n2.category == "COMMERCIAL" or any(k in n2.canonical_name.lower() for k in commercial_keywords)

                if is_c1 and is_c2:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=n1.intent_id,
                            target_intent_id=n2.intent_id,
                            relationship_type=IntentRelationshipType.COMPLEMENTARY,
                            strength=0.85,
                            reason=f"Complementary commercial intents: '{n1.canonical_name}' and '{n2.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return relationships


class SupportOperationalRule(RelationshipRule):
    """
    Identifies SUPPORTING relationships where operational or informational inquiries assist main actions.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="SupportOperationalRule",
            domain="CROSS_INDUSTRY",
            priority=30,
        )

    def evaluate_relationships(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []
        support_keywords = {"support", "help", "troubleshoot", "documentation", "faq", "inquiry", "status"}

        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if i == j:
                    continue
                n_support = nodes[i]
                n_target = nodes[j]

                if any(k in n_support.canonical_name.lower() for k in support_keywords) and n_target.category in ("COMMERCIAL", "OPERATIONAL"):
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=n_support.intent_id,
                            target_intent_id=n_target.intent_id,
                            relationship_type=IntentRelationshipType.SUPPORTING,
                            strength=0.75,
                            reason=f"Supportive inquiry '{n_support.canonical_name}' supports '{n_target.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return relationships


class CrossIntentRelatedRule(RelationshipRule):
    """
    Identifies general RELATED relationships for intents sharing domain category or high co-occurrence.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="CrossIntentRelatedRule",
            domain="CROSS_INDUSTRY",
            priority=50,
        )

    def evaluate_relationships(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentRelationship]:
        relationships: List[IntentRelationship] = []

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]

                # Check category match
                if n1.category == n2.category and n1.category != "GENERAL":
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=n1.intent_id,
                            target_intent_id=n2.intent_id,
                            relationship_type=IntentRelationshipType.RELATED,
                            strength=0.70,
                            reason=f"Shared intent category '{n1.category}' between '{n1.canonical_name}' and '{n2.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return relationships
