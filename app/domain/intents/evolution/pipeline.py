"""
HunterOS Engage V1 - Intent Evolution Pipeline
Orchestrates the deterministic 8-stage Intent Evolution Pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.domain.intents.evolution.context import IntentEvolutionContext
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.evolution.stages.stage1_load_history import LoadHistoricalSnapshotsStage
from app.domain.intents.evolution.stages.stage2_load_current import LoadCurrentSnapshotStage
from app.domain.intents.evolution.stages.stage3_normalize_state import NormalizeIntentStateStage
from app.domain.intents.evolution.stages.stage4_compare_snapshots import CompareSnapshotsStage
from app.domain.intents.evolution.stages.stage5_detect_evolution import DetectEvolutionStage
from app.domain.intents.evolution.stages.stage6_project_timelines import ProjectTimelinesStage
from app.domain.intents.evolution.stages.stage7_validate_evolution import ValidateEvolutionStage
from app.domain.intents.evolution.stages.stage8_generate_result import GenerateEvolutionResultStage
from app.domain.intents.evolution.strategies.registry import (
    EvolutionStrategyRegistry,
    default_evolution_strategy_registry,
)
from app.domain.intents.evolution.timelines.registry import (
    IntentTimelineRegistry,
    default_timeline_registry,
)
from app.domain.intents.evolution.validation import (
    EvolutionValidator,
    default_evolution_validator,
)

logger = logging.getLogger(__name__)


class IntentEvolutionPipeline:
    """
    Deterministic 8-stage pipeline executing intent evolution and timeline projections.
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        strategy_registry: Optional[EvolutionStrategyRegistry] = None,
        timeline_registry: Optional[IntentTimelineRegistry] = None,
        validator: Optional[EvolutionValidator] = None,
    ):
        self.repository = repository
        self.strategy_registry = strategy_registry or default_evolution_strategy_registry
        self.timeline_registry = timeline_registry or default_timeline_registry
        self.validator = validator or default_evolution_validator

        # Stages
        self.stage1 = LoadHistoricalSnapshotsStage(repository=self.repository)
        self.stage2 = LoadCurrentSnapshotStage()
        self.stage3 = NormalizeIntentStateStage()
        self.stage4 = CompareSnapshotsStage()
        self.stage5 = DetectEvolutionStage(strategy_registry=self.strategy_registry)
        self.stage6 = ProjectTimelinesStage(timeline_registry=self.timeline_registry)
        self.stage7 = ValidateEvolutionStage(validator=self.validator)
        self.stage8 = GenerateEvolutionResultStage()

    def execute(self, context: IntentEvolutionContext) -> IntentEvolutionResult:
        """
        Execute the 8-stage evolution pipeline sequentially.
        """
        logger.debug(f"Starting IntentEvolutionPipeline for entity={context.entity_id} (type={context.entity_type.value})")

        self.stage1.execute(context)
        self.stage2.execute(context)
        self.stage3.execute(context)
        self.stage4.execute(context)
        self.stage5.execute(context)
        self.stage6.execute(context)
        self.stage7.execute(context)
        self.stage8.execute(context)

        if not context.result:
            raise RuntimeError("IntentEvolutionPipeline failed to generate an IntentEvolutionResult.")

        return context.result
