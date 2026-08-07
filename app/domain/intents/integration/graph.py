"""
HunterOS Engage V1 - Intent Context Graph Builder & Relational Navigator
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Constructs the cross-subsystem relational IntentContextGraph connecting:
Detection -> Classification -> Evolution -> Resolution
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.models import (
    ContextGraphLink,
    ContextGraphLinkType,
    ContextGraphNode,
    IntentContextGraph,
)
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult


class IntentContextGraphBuilder:
    """
    Constructs the traceable cross-subsystem relational IntentContextGraph.
    Allows downstream modules to navigate relationships directly across all 4 intent phases.
    """

    def build_graph(
        self,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
    ) -> IntentContextGraph:
        graph = IntentContextGraph()

        # 1. Ingest Detection Nodes
        if detection_result and detection_result.detected_intents:
            for det in detection_result.detected_intents:
                node_id = f"det_{det.intent_id}"
                graph.add_node(
                    ContextGraphNode(
                        node_id=node_id,
                        subsystem="DETECTION",
                        intent_name=det.intent_type.value if hasattr(det.intent_type, "value") else str(det.intent_type),
                        confidence=det.confidence_score,
                        status="DETECTED",
                        attributes={
                            "taxonomy_category": det.category.value if hasattr(det.category, "value") else str(det.category),
                            "business_importance": det.business_importance.value if hasattr(det.business_importance, "value") else str(det.business_importance),
                        },
                        evidence_ids=det.supporting_evidence_message_ids or [],
                    )
                )

        # 2. Ingest Classification Nodes and link from Detection
        if classification_result and classification_result.classified_intents:
            for cls in classification_result.classified_intents:
                node_id = f"cls_{cls.original_intent_id}"
                graph.add_node(
                    ContextGraphNode(
                        node_id=node_id,
                        subsystem="CLASSIFICATION",
                        intent_name=cls.business_process,
                        confidence=cls.confidence,
                        status="CLASSIFIED",
                        attributes={
                            "business_category": cls.business_category.value if hasattr(cls.business_category, "value") else str(cls.business_category),
                            "business_domain": cls.business_domain.value if hasattr(cls.business_domain, "value") else str(cls.business_domain),
                            "taxonomy_path": cls.taxonomy_path,
                            "classification_method": cls.classification_method.value if hasattr(cls.classification_method, "value") else str(cls.classification_method),
                        },
                        evidence_ids=cls.supporting_evidence.source_message_ids if cls.supporting_evidence else [],
                    )
                )
                # Link Detection -> Classification
                det_node_id = f"det_{cls.original_intent_id}"
                if det_node_id in graph.nodes:
                    graph.add_link(
                        source_id=det_node_id,
                        target_id=node_id,
                        link_type=ContextGraphLinkType.CLASSIFIED_AS,
                    )

        # 3. Ingest Evolution Nodes and link from Classification / Detection
        if evolution_result and evolution_result.intent_histories:
            for evo in evolution_result.intent_histories:
                node_id = f"evo_{evo.intent_id}"
                state_val = evo.current_state.value if hasattr(evo.current_state, "value") else str(evo.current_state)
                graph.add_node(
                    ContextGraphNode(
                        node_id=node_id,
                        subsystem="EVOLUTION",
                        intent_name=evo.canonical_intent_name,
                        confidence=1.0,
                        status=state_val,
                        attributes={
                            "observation_count": getattr(evo, "observation_count", 1),
                            "trajectory_count": len(getattr(evo, "trajectory_path", getattr(evo, "trajectories", []))),
                        },
                        evidence_ids=[],
                    )
                )
                # Link Classification/Detection -> Evolution
                cls_node_id = f"cls_{evo.intent_id}"
                det_node_id = f"det_{evo.intent_id}"
                if cls_node_id in graph.nodes:
                    graph.add_link(
                        source_id=cls_node_id,
                        target_id=node_id,
                        link_type=ContextGraphLinkType.EVOLVED_INTO,
                    )
                elif det_node_id in graph.nodes:
                    graph.add_link(
                        source_id=det_node_id,
                        target_id=node_id,
                        link_type=ContextGraphLinkType.EVOLVED_INTO,
                    )

        # 4. Ingest Resolution Nodes, Resolution Groups, Dominance, Conflicts & Dependencies
        if resolution_result and resolution_result.resolution_graph:
            res_graph = resolution_result.resolution_graph

            # Nodes
            for node_key, node in res_graph.nodes.items():
                node_id = f"res_{node.intent_id}"
                graph.add_node(
                    ContextGraphNode(
                        node_id=node_id,
                        subsystem="RESOLUTION",
                        intent_name=node.canonical_name,
                        confidence=node.confidence,
                        status="RESOLVED",
                        attributes={
                            "raw_intent_type": node.raw_intent_type,
                            "lifecycle_state": node.lifecycle_state,
                        },
                        evidence_ids=node.evidence_message_ids,
                    )
                )
                # Link Evolution / Classification -> Resolution
                evo_node_id = f"evo_{node.intent_id}"
                cls_node_id = f"cls_{node.intent_id}"
                if evo_node_id in graph.nodes:
                    graph.add_link(
                        source_id=evo_node_id,
                        target_id=node_id,
                        link_type=ContextGraphLinkType.RESOLVED_IN,
                    )
                elif cls_node_id in graph.nodes:
                    graph.add_link(
                        source_id=cls_node_id,
                        target_id=node_id,
                        link_type=ContextGraphLinkType.RESOLVED_IN,
                    )

            # Resolution Groups & Dominance Links
            if resolution_result.resolved_groups:
                for grp in resolution_result.resolved_groups:
                    # Update resolution node attributes and add dominance links
                    if grp.dominant_intent:
                        dom_res_id = f"res_{grp.dominant_intent.intent_id}"
                        if dom_res_id in graph.nodes:
                            graph.nodes[dom_res_id].attributes["is_dominant"] = True
                            graph.nodes[dom_res_id].attributes["group_id"] = str(grp.group_id)
                            graph.nodes[dom_res_id].attributes["group_name"] = grp.name

                        for supp in grp.supporting_intents:
                            supp_res_id = f"res_{supp.intent_id}"
                            if supp_res_id in graph.nodes:
                                graph.nodes[supp_res_id].attributes["is_dominant"] = False
                                graph.nodes[supp_res_id].attributes["group_id"] = str(grp.group_id)
                                graph.nodes[supp_res_id].attributes["group_name"] = grp.name
                                if dom_res_id in graph.nodes:
                                    graph.add_link(
                                        source_id=dom_res_id,
                                        target_id=supp_res_id,
                                        link_type=ContextGraphLinkType.DOMINATES,
                                    )

            # Conflicts
            if res_graph.conflicts:
                for c in res_graph.conflicts:
                    for i in range(len(c.intent_ids)):
                        for j in range(i + 1, len(c.intent_ids)):
                            id_a = f"res_{c.intent_ids[i]}"
                            id_b = f"res_{c.intent_ids[j]}"
                            if id_a in graph.nodes and id_b in graph.nodes:
                                graph.add_link(
                                    source_id=id_a,
                                    target_id=id_b,
                                    link_type=ContextGraphLinkType.CONFLICTS_WITH,
                                    metadata={
                                        "conflict_type": c.conflict_type.value if hasattr(c.conflict_type, "value") else str(c.conflict_type),
                                        "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                                        "description": c.description,
                                    },
                                )

            # Dependencies
            if res_graph.dependencies:
                for d in res_graph.dependencies:
                    id_src = f"res_{d.source_intent_id}"
                    id_tgt = f"res_{d.target_intent_id}"
                    if id_src in graph.nodes and id_tgt in graph.nodes:
                        graph.add_link(
                            source_id=id_src,
                            target_id=id_tgt,
                            link_type=ContextGraphLinkType.DEPENDS_ON,
                            metadata={
                                "dependency_type": d.dependency_type.value if hasattr(d.dependency_type, "value") else str(d.dependency_type),
                                "is_blocking": d.is_blocking,
                                "reason": d.reason,
                            },
                        )

        return graph
