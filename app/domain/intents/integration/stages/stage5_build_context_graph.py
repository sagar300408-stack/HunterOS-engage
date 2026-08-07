"""
HunterOS Engage V1 - Stage 5: Build Context Graph
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.domain.intents.integration.context import IntentIntegrationPipelineContext
from app.domain.intents.integration.graph import IntentContextGraphBuilder

logger = logging.getLogger(__name__)


class Stage5_BuildContextGraph:
    """Builds the traceable cross-module IntentContextGraph."""

    def __init__(self, graph_builder: Optional[IntentContextGraphBuilder] = None) -> None:
        self.graph_builder = graph_builder or IntentContextGraphBuilder()

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        profile = ctx.active_profile
        inc_det = profile.include_detection if profile else True
        inc_cls = profile.include_classification if profile else True
        inc_evo = profile.include_evolution if profile else True
        inc_res = profile.include_resolution if profile else True

        ctx.context_graph = self.graph_builder.build_graph(
            detection_result=ctx.detection_result if inc_det else None,
            classification_result=ctx.classification_result if inc_cls else None,
            evolution_result=ctx.evolution_result if inc_evo else None,
            resolution_result=ctx.resolution_result if inc_res else None,
        )

        logger.debug(
            "Stage 5 Built Context Graph: %d nodes, %d links",
            len(ctx.context_graph.nodes),
            len(ctx.context_graph.links),
        )
        ctx.stage_timings_ms["stage5_build_context_graph_ms"] = (time.perf_counter() - start) * 1000
