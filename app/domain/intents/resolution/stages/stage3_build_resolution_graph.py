"""
HunterOS Engage V1 - Stage 3: Build Resolution Graph
Constructs the initial immutable IntentResolutionGraph snapshot from normalized nodes.
"""

from __future__ import annotations

import time

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import IntentResolutionGraph


class Stage3_BuildResolutionGraph:
    """
    Stage 3: Constructs the foundational IntentResolutionGraph containing all active nodes.
    Subsequent relationship, conflict, and dependency analyzers read this shared graph.
    """

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()

        context.resolution_graph = IntentResolutionGraph(
            nodes=dict(context.normalized_nodes),
            edges=[],
            conflicts=[],
            dependencies=[],
        )

        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage3_BuildResolutionGraph", duration)
