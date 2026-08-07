"""
HunterOS Engage V1 - Dependency Resolution Rules
Deterministic rules for identifying sequential, prerequisite, and blocking dependencies.
"""

from __future__ import annotations

from typing import List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentResolutionGraph,
)
from app.domain.intents.resolution.rules.base import DependencyRule


class SequentialRequirementRule(DependencyRule):
    """
    Identifies REQUIRED sequential business dependencies (e.g. Verification -> Account Change).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="SequentialRequirementRule",
            domain="CROSS_INDUSTRY",
            priority=10,
        )

    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        dependencies: List[IntentDependency] = []

        auth_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("auth", "verify", "identity", "kyc", "security_check"))]
        account_change_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("change_password", "transfer", "update_billing", "change_email", "payout"))]

        for a in auth_nodes:
            for ac in account_change_nodes:
                if a.intent_id != ac.intent_id:
                    dependencies.append(
                        IntentDependency(
                            dependency_type=IntentDependencyType.REQUIRED,
                            source_intent_id=a.intent_id,
                            target_intent_id=ac.intent_id,
                            is_blocking=True,
                            evidence_ids=list(set(a.evidence_message_ids + ac.evidence_message_ids)),
                            reason=f"Identity/Auth verification '{a.canonical_name}' is a required prerequisite for '{ac.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return dependencies


class PrerequisiteInquiryRule(DependencyRule):
    """
    Identifies SEQUENTIAL commercial inquiry dependencies (e.g. Demo / Evaluation -> Purchase / Contract).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="PrerequisiteInquiryRule",
            domain="CROSS_INDUSTRY",
            priority=20,
        )

    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        dependencies: List[IntentDependency] = []

        eval_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("demo", "trial", "evaluation", "quote", "pricing_inquiry"))]
        contract_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("contract", "purchase", "sign_agreement", "order_confirmation"))]

        for e in eval_nodes:
            for c in contract_nodes:
                if e.intent_id != c.intent_id:
                    dependencies.append(
                        IntentDependency(
                            dependency_type=IntentDependencyType.SEQUENTIAL,
                            source_intent_id=e.intent_id,
                            target_intent_id=c.intent_id,
                            is_blocking=False,
                            evidence_ids=list(set(e.evidence_message_ids + c.evidence_message_ids)),
                            reason=f"Evaluation inquiry '{e.canonical_name}' naturally precedes contract execution '{c.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return dependencies


class BlockingSupportRule(DependencyRule):
    """
    Identifies BLOCKING dependencies where a critical unresolved support issue blocks commercial progress.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="BlockingSupportRule",
            domain="CROSS_INDUSTRY",
            priority=30,
        )

    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        dependencies: List[IntentDependency] = []

        bug_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("outage", "critical_bug", "data_loss", "system_down", "security_incident"))]
        expansion_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in ("upgrade", "renew", "expand", "upsell"))]

        for b in bug_nodes:
            for exp in expansion_nodes:
                if b.intent_id != exp.intent_id:
                    dependencies.append(
                        IntentDependency(
                            dependency_type=IntentDependencyType.BLOCKING,
                            source_intent_id=b.intent_id,
                            target_intent_id=exp.intent_id,
                            is_blocking=True,
                            evidence_ids=list(set(b.evidence_message_ids + exp.evidence_message_ids)),
                            reason=f"Unresolved critical issue '{b.canonical_name}' blocks positive commercial expansion '{exp.canonical_name}'",
                            rule_name=self.rule_name,
                        )
                    )
        return dependencies
