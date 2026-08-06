"""
HunterOS Engage V1 - Abstract Intent Rule Base
Base contract for deterministic rule-based intent detectors.
"""

from __future__ import annotations

import abc
import uuid
from typing import List, Optional

from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    EvidenceEdge,
    EvidenceNode,
    EvidenceNodeType,
    IntentDetectionMethod,
    IntentEvidence,
    IntentEvidenceGraph,
    IntentProvenance,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.taxonomy import IntentTaxonomy


class AbstractIntentRule(abc.ABC):
    """Abstract base class for all deterministic intent rules."""

    @property
    @abc.abstractmethod
    def rule_name(self) -> str:
        """Unique identifier of the rule."""
        pass

    @property
    def rule_version(self) -> str:
        """Version string of the rule."""
        return "1.0.0"

    @property
    @abc.abstractmethod
    def target_intent_types(self) -> List[IntentType]:
        """The list of intent types this rule is capable of detecting."""
        pass

    @abc.abstractmethod
    def evaluate(self, context: IntentDetectionContext) -> List[DetectedIntent]:
        """
        Evaluate context against deterministic pattern and facts.
        Returns:
            List of detected candidate intent instances.
        """
        pass

    # ── Factory Helpers for Rules ───────────────────────────────────────────

    def create_intent(
        self,
        context: IntentDetectionContext,
        intent_type: IntentType,
        title: str,
        description: str,
        confidence: float,
        detection_method: IntentDetectionMethod,
        evidence: IntentEvidence,
        rule_pack_name: str = "CoreRulePack",
        business_importance: Optional[BusinessImportance] = None,
        custom_category: Optional[IntentTaxonomyCategory] = None,
    ) -> DetectedIntent:
        """Helper to build a fully structured DetectedIntent with taxonomy, provenance, and graph."""
        taxonomy_node = IntentTaxonomy.get_node(intent_type)
        category = custom_category or taxonomy_node.category
        importance = business_importance or taxonomy_node.default_importance

        # Build evidence graph if not provided
        evidence_graph = evidence.evidence_graph
        if evidence_graph is None and evidence.has_sufficient_evidence:
            nodes: List[EvidenceNode] = []
            edges: List[EvidenceEdge] = []
            root_node_id = f"intent-{intent_type.value.lower()}"

            for mid in evidence.source_message_ids:
                n_id = f"msg-{mid}"
                nodes.append(
                    EvidenceNode(
                        node_id=n_id,
                        node_type=EvidenceNodeType.MESSAGE,
                        title=f"Source Message {mid}",
                        snippet=evidence.text_snippets[0] if evidence.text_snippets else None,
                    )
                )
                edges.append(
                    EvidenceEdge(
                        source_node_id=root_node_id,
                        target_node_id=n_id,
                        relation_type="TRIGGERED_BY",
                    )
                )

            for fid in evidence.source_fact_ids:
                n_id = f"fact-{fid}"
                nodes.append(
                    EvidenceNode(
                        node_id=n_id,
                        node_type=EvidenceNodeType.FACT,
                        title=f"Extracted Fact {fid}",
                    )
                )
                edges.append(
                    EvidenceEdge(
                        source_node_id=root_node_id,
                        target_node_id=n_id,
                        relation_type="CORROBORATED_BY",
                    )
                )

            for eid in evidence.source_event_ids:
                n_id = f"event-{eid}"
                nodes.append(
                    EvidenceNode(
                        node_id=n_id,
                        node_type=EvidenceNodeType.TIMELINE_EVENT,
                        title=f"Timeline Event {eid}",
                    )
                )
                edges.append(
                    EvidenceEdge(
                        source_node_id=root_node_id,
                        target_node_id=n_id,
                        relation_type="EVIDENCED_BY",
                    )
                )

            evidence_graph = IntentEvidenceGraph(nodes=nodes, edges=edges)

        complete_evidence = IntentEvidence(
            source_message_ids=evidence.source_message_ids,
            source_event_ids=evidence.source_event_ids,
            source_fact_ids=evidence.source_fact_ids,
            source_milestone_ids=evidence.source_milestone_ids,
            source_moment_ids=evidence.source_moment_ids,
            source_insight_ids=evidence.source_insight_ids,
            source_topic_names=evidence.source_topic_names,
            text_snippets=evidence.text_snippets,
            detection_method=detection_method,
            confidence_score=confidence,
            evidence_graph=evidence_graph,
            metadata=evidence.metadata,
        )

        provenance = IntentProvenance(
            intent_version="1.0.0",
            detector_version="1.0.0",
            rule_version=self.rule_version,
            rule_pack_name=rule_pack_name,
            rule_name=self.rule_name,
        )

        return DetectedIntent(
            intent_id=uuid.uuid4(),
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            intent_type=intent_type,
            taxonomy_category=category,
            taxonomy_path=taxonomy_node.taxonomy_path,
            business_importance=importance,
            title=title,
            description=description,
            confidence=round(confidence, 3),
            detection_method=detection_method,
            supporting_evidence=complete_evidence,
            provenance=provenance,
        )
