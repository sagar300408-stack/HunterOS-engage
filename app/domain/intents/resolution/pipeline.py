"""
HunterOS Engage V1 - Multi-Intent Resolution Pipeline
Coordinating pipeline for the 9 sequential multi-intent resolution stages.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import MultiIntentResolutionResult
from app.domain.intents.resolution.registry import IntentResolutionRegistry, default_resolution_registry
from app.domain.intents.resolution.stages.stage1_load_artifacts import Stage1_LoadIntentArtifacts
from app.domain.intents.resolution.stages.stage2_normalize_nodes import Stage2_NormalizeIntentNodes
from app.domain.intents.resolution.stages.stage3_build_resolution_graph import Stage3_BuildResolutionGraph
from app.domain.intents.resolution.stages.stage4_analyze_relationships import Stage4_AnalyzeRelationships
from app.domain.intents.resolution.stages.stage5_analyze_conflicts import Stage5_AnalyzeConflicts
from app.domain.intents.resolution.stages.stage6_analyze_dependencies import Stage6_AnalyzeDependencies
from app.domain.intents.resolution.stages.stage7_resolve_groups_dominance import Stage7_ResolveGroupsAndDominance
from app.domain.intents.resolution.stages.stage8_validate_resolution import Stage8_ValidateResolution
from app.domain.intents.resolution.stages.stage9_generate_result import Stage9_GenerateResolutionResult

logger = logging.getLogger(__name__)


class MultiIntentResolutionPipeline:
    """
    Deterministic 9-stage pipeline for Multi-Intent Resolution.
    """

    def __init__(self, registry: Optional[IntentResolutionRegistry] = None) -> None:
        reg = registry or default_resolution_registry
        self.stage1 = Stage1_LoadIntentArtifacts()
        self.stage2 = Stage2_NormalizeIntentNodes()
        self.stage3 = Stage3_BuildResolutionGraph()
        self.stage4 = Stage4_AnalyzeRelationships(registry=reg)
        self.stage5 = Stage5_AnalyzeConflicts(registry=reg)
        self.stage6 = Stage6_AnalyzeDependencies(registry=reg)
        self.stage7 = Stage7_ResolveGroupsAndDominance(registry=reg)
        self.stage8 = Stage8_ValidateResolution()
        self.stage9 = Stage9_GenerateResolutionResult()

    def run(self, context: MultiIntentResolutionContext) -> MultiIntentResolutionResult:
        """
        Execute all 9 stages in strict order.
        """
        self.stage1.execute(context)
        self.stage2.execute(context)
        self.stage3.execute(context)
        self.stage4.execute(context)
        self.stage5.execute(context)
        self.stage6.execute(context)
        self.stage7.execute(context)
        self.stage8.execute(context)
        self.stage9.execute(context)

        if not context.result:
            raise RuntimeError("MultiIntentResolutionPipeline failed to produce result aggregate root.")

        return context.result
