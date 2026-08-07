"""
HunterOS Engage V1 - Real Estate Resolution Plugin
Vertical rules and strategies for property showings, mortgage pre-approvals, and purchase offers.
"""

from __future__ import annotations

from typing import List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceStrategy
from app.domain.intents.resolution.dominance.commercial import CommercialImportanceStrategy
from app.domain.intents.resolution.dominance.evidence_coverage import EvidenceCoverageStrategy
from app.domain.intents.resolution.models import (
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
)
from app.domain.intents.resolution.plugins.base import IndustryResolutionPlugin
from app.domain.intents.resolution.rules.base import ConflictRule, DependencyRule, RelationshipRule


class RealEstateMortgagePreapprovalDependencyRule(DependencyRule):
    """
    Mortgage pre-approval is a prerequisite dependency before formal offer submission.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="RealEstateMortgagePreapprovalDependencyRule",
            domain="REAL_ESTATE",
            priority=15,
        )

    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        deps: List[IntentDependency] = []

        mortgage_nodes = [n for n in nodes if "mortgage" in n.canonical_name.lower() or "financing" in n.canonical_name.lower()]
        offer_nodes = [n for n in nodes if "offer" in n.canonical_name.lower() or "purchase_contract" in n.canonical_name.lower()]

        for m in mortgage_nodes:
            for o in offer_nodes:
                if m.intent_id != o.intent_id:
                    deps.append(
                        IntentDependency(
                            dependency_type=IntentDependencyType.REQUIRED,
                            source_intent_id=m.intent_id,
                            target_intent_id=o.intent_id,
                            is_blocking=True,
                            evidence_ids=list(set(m.evidence_message_ids + o.evidence_message_ids)),
                            reason=f"Financing verification '{m.canonical_name}' is a required prerequisite for submitting offer '{o.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return deps


class RealEstateShowingConflictRule(ConflictRule):
    """
    Detects showing schedule conflicts (e.g. Schedule Tour vs Cancel Tour).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="RealEstateShowingConflictRule",
            domain="REAL_ESTATE",
            priority=15,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []

        book_nodes = [n for n in nodes if "schedule_tour" in n.canonical_name.lower() or "book_showing" in n.canonical_name.lower()]
        cancel_nodes = [n for n in nodes if "cancel_tour" in n.canonical_name.lower() or "cancel_showing" in n.canonical_name.lower()]

        for b in book_nodes:
            for c in cancel_nodes:
                conflicts.append(
                    IntentConflict(
                        conflict_type=IntentConflictType.MUTUALLY_EXCLUSIVE,
                        severity=IntentConflictSeverity.HIGH,
                        intent_ids=[b.intent_id, c.intent_id],
                        description=f"Showing appointment conflict: '{b.canonical_name}' vs '{c.canonical_name}'",
                        evidence_ids=list(set(b.evidence_message_ids + c.evidence_message_ids)),
                        resolution_hint="Confirm tour attendance status with the prospective buyer/renter.",
                        rule_name=self.rule_name,
                    )
                )
        return conflicts


class RealEstateResolutionPlugin(IndustryResolutionPlugin):
    """Real estate industry resolution plugin."""

    def __init__(self) -> None:
        super().__init__(
            plugin_name="RealEstateResolutionPlugin",
            domain="REAL_ESTATE",
            version="1.0.0",
        )

    def get_relationship_rules(self) -> List[RelationshipRule]:
        return []

    def get_conflict_rules(self) -> List[ConflictRule]:
        return [RealEstateShowingConflictRule()]

    def get_dependency_rules(self) -> List[DependencyRule]:
        return [RealEstateMortgagePreapprovalDependencyRule()]

    def get_dominance_strategies(self) -> List[DominanceStrategy]:
        return [
            EvidenceCoverageStrategy(weight=1.5),
            CommercialImportanceStrategy(weight=1.5),
        ]
