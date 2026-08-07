"""
HunterOS Engage V1 - Stage 6: Analyze Dependencies
Discovers sequential, required, prerequisite, and blocking dependencies between intents.
"""

from __future__ import annotations

import time
from typing import List, Optional

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import IntentDependency
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry


class Stage6_AnalyzeDependencies:
    """
    Stage 6: Executes dependency rules against the shared resolution graph.
    """

    def __init__(self, registry: Optional[IntentResolutionRegistry] = None) -> None:
        self.registry = registry or default_resolution_registry

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        nodes = list(context.normalized_nodes.values())
        graph = context.resolution_graph

        rules = self.registry.get_dependency_rules(rule_pack_names=context.rule_pack_names)
        context.rules_evaluated_count += len(rules)

        dependencies: List[IntentDependency] = []
        for rule in rules:
            found = rule.evaluate_dependencies(nodes, graph, context)
            dependencies.extend(found)
            if found and rule.rule_name not in context.rule_packs_applied:
                context.rule_packs_applied.append(rule.rule_name)

        context.analyzed_dependencies = dependencies

        # Update resolution graph with analyzed dependencies
        if context.resolution_graph:
            context.resolution_graph = context.resolution_graph.model_copy(update={"dependencies": dependencies})

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage6_AnalyzeDependencies", duration)
