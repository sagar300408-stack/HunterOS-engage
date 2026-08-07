"""
HunterOS Engage V1 - Conflict Resolution Rules
Deterministic rules for identifying duplicates, contradictions, competing, and mutually exclusive intents.
"""

from __future__ import annotations

from typing import List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentNode,
    IntentResolutionGraph,
)
from app.domain.intents.resolution.rules.base import ConflictRule


class DuplicateIntentRule(ConflictRule):
    """
    Identifies duplicate intent nodes representing identical canonical intent types.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="DuplicateIntentRule",
            domain="CROSS_INDUSTRY",
            priority=10,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []
        name_map = {}

        for n in nodes:
            key = n.canonical_name.lower().strip()
            name_map.setdefault(key, []).append(n)

        for key, matching_nodes in name_map.items():
            if len(matching_nodes) > 1:
                conflict_ids = [n.intent_id for n in matching_nodes]
                ev_ids = [eid for n in matching_nodes for eid in n.evidence_message_ids]
                conflicts.append(
                    IntentConflict(
                        conflict_type=IntentConflictType.DUPLICATE,
                        severity=IntentConflictSeverity.LOW,
                        intent_ids=conflict_ids,
                        description=f"Duplicate intent detected: {len(matching_nodes)} nodes with canonical name '{matching_nodes[0].canonical_name}'",
                        evidence_ids=list(set(ev_ids)),
                        resolution_hint="Consolidate duplicate intent nodes into a single canonical intent representation.",
                        rule_name=self.rule_name,
                    )
                )
        return conflicts


class MutuallyExclusiveIntentRule(ConflictRule):
    """
    Identifies mutually exclusive intents (e.g. Purchase/Renew vs Cancel/Terminate).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="MutuallyExclusiveIntentRule",
            domain="CROSS_INDUSTRY",
            priority=20,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []
        positive_keywords = {"purchase", "buy", "renew", "subscribe", "upgrade", "expand", "adopt", "schedule", "demo", "meeting", "pricing", "interest", "quote", "proposal"}
        negative_keywords = {"cancel", "churn", "terminate", "close_account", "refund", "downgrade", "competitor", "rejection", "decline"}

        pos_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in positive_keywords)]
        neg_nodes = [n for n in nodes if any(k in n.canonical_name.lower() for k in negative_keywords)]

        for p in pos_nodes:
            for n in neg_nodes:
                conflicts.append(
                    IntentConflict(
                        conflict_type=IntentConflictType.MUTUALLY_EXCLUSIVE,
                        severity=IntentConflictSeverity.HIGH,
                        intent_ids=[p.intent_id, n.intent_id],
                        description=f"Mutually exclusive intents detected: Positive motion '{p.canonical_name}' vs Terminating motion '{n.canonical_name}'",
                        evidence_ids=list(set(p.evidence_message_ids + n.evidence_message_ids)),
                        resolution_hint="Clarify account status: customer displays both retention/purchase and churn/termination intent signals.",
                        rule_name=self.rule_name,
                    )
                )
        return conflicts


class ContradictingIntentRule(ConflictRule):
    """
    Identifies contradicting directional signals (e.g. Upgrade vs Downgrade).
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="ContradictingIntentRule",
            domain="CROSS_INDUSTRY",
            priority=30,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []

        upgrade_nodes = [n for n in nodes if "upgrade" in n.canonical_name.lower() or "expand" in n.canonical_name.lower()]
        downgrade_nodes = [n for n in nodes if "downgrade" in n.canonical_name.lower() or "reduce" in n.canonical_name.lower()]

        for u in upgrade_nodes:
            for d in downgrade_nodes:
                conflicts.append(
                    IntentConflict(
                        conflict_type=IntentConflictType.CONTRADICTING,
                        severity=IntentConflictSeverity.MEDIUM,
                        intent_ids=[u.intent_id, d.intent_id],
                        description=f"Contradicting intent trajectory: '{u.canonical_name}' vs '{d.canonical_name}'",
                        evidence_ids=list(set(u.evidence_message_ids + d.evidence_message_ids)),
                        resolution_hint="Review recent conversation context to determine latest customer position.",
                        rule_name=self.rule_name,
                    )
                )
        return conflicts


class TimelineStateConflictRule(ConflictRule):
    """
    Identifies timeline conflicts where an intent is marked resolved/closed while another active node represents the same issue.
    """

    def __init__(self) -> None:
        super().__init__(
            rule_name="TimelineStateConflictRule",
            domain="CROSS_INDUSTRY",
            priority=40,
        )

    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        conflicts: List[IntentConflict] = []

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]

                if n1.category == n2.category and n1.canonical_name == n2.canonical_name:
                    if (n1.lifecycle_state in ("RESOLVED", "CLOSED") and n2.lifecycle_state in ("ACTIVE", "STRENGTHENING", "NEW")) or \
                       (n2.lifecycle_state in ("RESOLVED", "CLOSED") and n1.lifecycle_state in ("ACTIVE", "STRENGTHENING", "NEW")):
                        conflicts.append(
                            IntentConflict(
                                conflict_type=IntentConflictType.TIMELINE_CONFLICT,
                                severity=IntentConflictSeverity.MEDIUM,
                                intent_ids=[n1.intent_id, n2.intent_id],
                                description=f"Timeline state contradiction for '{n1.canonical_name}': one node is {n1.lifecycle_state} while another is {n2.lifecycle_state}",
                                evidence_ids=list(set(n1.evidence_message_ids + n2.evidence_message_ids)),
                                resolution_hint="Re-evaluate lifecycle progression against conversation timestamps.",
                                rule_name=self.rule_name,
                            )
                        )
        return conflicts
