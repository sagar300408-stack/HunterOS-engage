"""
HunterOS Engage V1 - Evolution Pipeline Stage 5: Detect Intent Evolution
Executes registered evolution strategies and appends resulting events to the immutable stream.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from app.domain.intents.evolution.strategies.registry import (
    EvolutionStrategyRegistry,
    default_evolution_strategy_registry,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class DetectEvolutionStage:
    """
    Stage 5: Evaluates strategies (Lifecycle, Transition, Confidence, Merge/Split, Industry)
    and populates the IntentEvolutionEventStream.
    """

    def __init__(self, strategy_registry: Optional[EvolutionStrategyRegistry] = None):
        self.strategy_registry = strategy_registry or default_evolution_strategy_registry

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()

        strategy_results = self.strategy_registry.evaluate_all(context)

        for res in strategy_results:
            for ev in res.events:
                context.append_event(ev)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage5_DetectEvolution", elapsed_ms)
