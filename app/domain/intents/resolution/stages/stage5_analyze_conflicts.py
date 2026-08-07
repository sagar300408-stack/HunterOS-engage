"""
HunterOS Engage V1 - Stage 5: Analyze Conflicts
Detects factual conflicts, duplicates, contradicting trajectories, and mutually exclusive intents.
"""

from __future__ import annotations

import time
from typing import List, Optional

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import IntentConflict
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry


class Stage5_AnalyzeConflicts:
    """
    Stage 5: Executes conflict rules against the shared resolution graph.
    """

    def __init__(self, registry: Optional[IntentResolutionRegistry] = None) -> None:
        self.registry = registry or default_resolution_registry

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        nodes = list(context.normalized_nodes.values())
        graph = context.resolution_graph

        rules = self.registry.get_conflict_rules(rule_pack_names=context.rule_pack_names)
        context.rules_evaluated_count += len(rules)

        conflicts: List[IntentConflict] = []
        for rule in rules:
            found = rule.evaluate_conflicts(nodes, graph, context)
            conflicts.extend(found)
            if found and rule.rule_name not in context.rule_packs_applied:
                context.rule_packs_applied.append(rule.rule_name)

        context.analyzed_conflicts = conflicts

        # Update resolution graph with analyzed conflicts
        if context.resolution_graph:
            context.resolution_graph = context.resolution_graph.model_copy(update={"conflicts": conflicts})

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage5_AnalyzeConflicts", duration)
