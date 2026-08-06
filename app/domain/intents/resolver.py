"""
HunterOS Engage V1 - Intent Resolver
Resolves candidate intent duplicates, merges multi-source evidence graphs, and decides canonical survivors.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from app.domain.intents.models import (
    DetectedIntent,
    EvidenceEdge,
    EvidenceNode,
    IntentEvidence,
    IntentEvidenceGraph,
    IntentType,
)


class IntentResolver:
    """
    Deduplicates and reconciles candidate intents.
    Merges evidence from multiple rules detecting the same underlying intent.
    """

    def resolve(
        self, candidate_intents: List[DetectedIntent]
    ) -> Tuple[List[DetectedIntent], int]:
        """
        Resolve duplicates among candidate intents.
        Returns:
            Tuple of (resolved canonical intents, count of resolved conflicts).
        """
        if not candidate_intents:
            return [], 0

        # Group by IntentType
        grouped: Dict[IntentType, List[DetectedIntent]] = defaultdict(list)
        for intent in candidate_intents:
            grouped[intent.intent_type].append(intent)

        resolved: List[DetectedIntent] = []
        conflict_count = 0

        for itype, group in grouped.items():
            if len(group) == 1:
                resolved.append(group[0])
                continue

            conflict_count += len(group) - 1

            # Select candidate with highest confidence as canonical baseline
            best_intent = max(group, key=lambda i: i.confidence)

            # Union evidence from all candidates in the group
            merged_msg_ids: Set[str] = set()
            merged_event_ids = set()
            merged_fact_ids = set()
            merged_milestone_ids = set()
            merged_moment_ids = set()
            merged_insight_ids = set()
            merged_topic_names: Set[str] = set()
            merged_snippets: List[str] = []
            merged_nodes: List[EvidenceNode] = []
            merged_edges: List[EvidenceEdge] = []
            seen_node_ids: Set[str] = set()

            for item in group:
                ev = item.supporting_evidence
                merged_msg_ids.update(ev.source_message_ids)
                merged_event_ids.update(ev.source_event_ids)
                merged_fact_ids.update(ev.source_fact_ids)
                merged_milestone_ids.update(ev.source_milestone_ids)
                merged_moment_ids.update(ev.source_moment_ids)
                merged_insight_ids.update(ev.source_insight_ids)
                merged_topic_names.update(ev.source_topic_names)
                for snip in ev.text_snippets:
                    if snip and snip not in merged_snippets:
                        merged_snippets.append(snip)

                if ev.evidence_graph:
                    for node in ev.evidence_graph.nodes:
                        if node.node_id not in seen_node_ids:
                            seen_node_ids.add(node.node_id)
                            merged_nodes.append(node)
                    for edge in ev.evidence_graph.edges:
                        merged_edges.append(edge)

            merged_graph = (
                IntentEvidenceGraph(nodes=merged_nodes, edges=merged_edges)
                if merged_nodes
                else best_intent.supporting_evidence.evidence_graph
            )

            merged_evidence = IntentEvidence(
                source_message_ids=sorted(list(merged_msg_ids)),
                source_event_ids=list(merged_event_ids),
                source_fact_ids=list(merged_fact_ids),
                source_milestone_ids=list(merged_milestone_ids),
                source_moment_ids=list(merged_moment_ids),
                source_insight_ids=list(merged_insight_ids),
                source_topic_names=sorted(list(merged_topic_names)),
                text_snippets=merged_snippets,
                detection_method=best_intent.detection_method,
                confidence_score=best_intent.confidence,
                evidence_graph=merged_graph,
                metadata=dict(best_intent.supporting_evidence.metadata),
            )

            canonical = DetectedIntent(
                intent_id=best_intent.intent_id,
                conversation_id=best_intent.conversation_id,
                workspace_id=best_intent.workspace_id,
                customer_id=best_intent.customer_id,
                intent_type=best_intent.intent_type,
                taxonomy_category=best_intent.taxonomy_category,
                taxonomy_path=best_intent.taxonomy_path,
                business_importance=best_intent.business_importance,
                title=best_intent.title,
                description=best_intent.description,
                confidence=best_intent.confidence,
                detection_method=best_intent.detection_method,
                supporting_evidence=merged_evidence,
                provenance=best_intent.provenance,
                detected_at=best_intent.detected_at,
                metadata=dict(best_intent.metadata),
            )
            resolved.append(canonical)

        # Sort by confidence descending
        resolved.sort(key=lambda i: i.confidence, reverse=True)
        return resolved, conflict_count


# Default singleton instance
default_intent_resolver = IntentResolver()
