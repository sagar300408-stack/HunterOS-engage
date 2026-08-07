"""
HunterOS Engage V1 - Healthcare Resolution Plugin
Vertical rules and strategies for patient scheduling, insurance verification, and prescriptions.
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
    IntentResolutionGraph,
)
from app.domain.intents.resolution.plugins.base import IndustryResolutionPlugin
from app.domain.intents.resolution.rules.base import ConflictRule, DependencyRule, RelationshipRule


class HealthcareInsuranceVerificationDependencyRule(DependencyRule):
    """
    Insurance eligibility verification is a prerequisite before scheduling elective procedures.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="HealthcareInsuranceVerificationDependencyRule",
            domain="HEALTHCARE",
            priority=15,
        )

    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        deps: List[IntentDependency] = []

        ins_nodes = [n for n in nodes if "insurance" in n.canonical_name.lower() or "coverage" in n.canonical_name.lower()]
        proc_nodes = [n for n in nodes if "procedure" in n.canonical_name.lower() or "surgery" in n.canonical_name.lower() or "specialist" in n.canonical_name.lower()]

        for i in ins_nodes:
            for p in proc_nodes:
                if i.intent_id != p.intent_id:
                    deps.append(
                        IntentDependency(
                            dependency_type=IntentDependencyType.REQUIRED,
                            source_intent_id=i.intent_id,
                            target_intent_id=p.intent_id,
                            is_blocking=True,
                            evidence_ids=list(set(i.evidence_message_ids + p.evidence_message_ids)),
                            reason=f"Insurance coverage verification '{i.canonical_name}' is a required prerequisite for '{p.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return deps


class HealthcareAppointmentConflictRule(ConflictRule):
    """
    Identifies appointment scheduling conflicts.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="HealthcareAppointmentConflictRule",
            domain="HEALTHCARE",
            priority=15,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []

        book_nodes = [n for n in nodes if "schedule_appointment" in n.canonical_name.lower() or "book_visit" in n.canonical_name.lower()]
        cancel_nodes = [n for n in nodes if "cancel_appointment" in n.canonical_name.lower() or "cancel_visit" in n.canonical_name.lower()]

        for b in book_nodes:
            for c in cancel_nodes:
                conflicts.append(
                    IntentConflict(
                        conflict_type=IntentConflictType.MUTUALLY_EXCLUSIVE,
                        severity=IntentConflictSeverity.HIGH,
                        intent_ids=[b.intent_id, c.intent_id],
                        description=f"Appointment scheduling conflict: '{b.canonical_name}' vs '{c.canonical_name}'",
                        evidence_ids=list(set(b.evidence_message_ids + c.evidence_message_ids)),
                        resolution_hint="Clarify appointment slot booking status with patient.",
                        rule_name=self.rule_name,
                    )
                )
        return conflicts


class HealthcareResolutionPlugin(IndustryResolutionPlugin):
    """Healthcare industry resolution plugin."""

    def __init__(self) -> None:
        super().__init__(
            plugin_name="HealthcareResolutionPlugin",
            domain="HEALTHCARE",
            version="1.0.0",
        )

    def get_relationship_rules(self) -> List[RelationshipRule]:
        return []

    def get_conflict_rules(self) -> List[ConflictRule]:
        return [HealthcareAppointmentConflictRule()]

    def get_dependency_rules(self) -> List[DependencyRule]:
        return [HealthcareInsuranceVerificationDependencyRule()]

    def get_dominance_strategies(self) -> List[DominanceStrategy]:
        return [
            EvidenceCoverageStrategy(weight=1.6),
            CommercialImportanceStrategy(weight=1.0),
        ]
