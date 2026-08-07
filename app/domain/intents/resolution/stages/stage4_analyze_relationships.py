"""
HunterOS Engage V1 - Stage 4: Analyze Relationships
Evaluates deterministic relationship rules to discover parent/child, complementary, supporting, and related edges.
"""

from __future__ import annotations

import time
from typing import List, Optional

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import IntentRelationship
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry


class Stage4_AnalyzeRelationships:
    """
    Stage 4: Executes relationship rules against the shared resolution graph.
    """

    def __init__(self, registry: Optional[IntentResolutionRegistry] = None) -> None:
        self.registry = registry or default_resolution_registry

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        nodes = list(context.normalized_nodes.values())
        graph = context.resolution_graph

        rules = self.registry.get_relationship_rules(rule_pack_names=context.rule_pack_names)
        context.rules_evaluated_count += len(rules)

        relationships: List[IntentRelationship] = []
        for rule in rules:
            found = rule.evaluate_relationships(nodes, graph, context)
            relationships.extend(found)
            if found and rule.rule_name not in context.rule_packs_applied:
                context.rule_packs_applied.append(rule.rule_name)

        # Ingest existing relationships from classification if present
        if context.classification_result:
            for r in getattr(context.classification_result, "relationships", []):
                src_id = getattr(r, "source_intent_id", None)
                tgt_id = getattr(r, "target_intent_id", None)
                if src_id and tgt_id and str(src_id) in context.normalized_nodes and str(tgt_id) in context.normalized_nodes:
                    relationships.append(
                        IntentRelationship(
                            source_intent_id=src_id,
                            target_intent_id=tgt_id,
                            relationship_type=getattr(r, "relationship_type", "RELATED"),
                            strength=float(getattr(r, "confidence", 0.9)),
                            reason=getattr(r, "reason", "Inherited from classification"),
                            rule_name="ClassificationInheritance",
                        )
                    )

        context.analyzed_relationships = relationships

        # Update resolution graph with analyzed edges
        if context.resolution_graph:
            context.resolution_graph = context.resolution_graph.model_copy(update={"edges": relationships})

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage4_AnalyzeRelationships", duration)
