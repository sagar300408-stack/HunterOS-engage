"""
HunterOS Engage V1 - Evolution Strategy Registry
Thread-safe catalog and execution coordinator for evolution strategies.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Dict, List, Optional

from app.domain.intents.evolution.strategies.base import (
    AbstractEvolutionStrategy,
    StrategyEvaluationResult,
)
from app.domain.intents.evolution.strategies.confidence import ConfidenceStrategy
from app.domain.intents.evolution.strategies.industry.cross_industry import CrossIndustryEvolutionStrategy
from app.domain.intents.evolution.strategies.industry.healthcare import HealthcareEvolutionStrategy
from app.domain.intents.evolution.strategies.industry.real_estate import RealEstateEvolutionStrategy
from app.domain.intents.evolution.strategies.lifecycle import LifecycleStrategy
from app.domain.intents.evolution.strategies.merge_split import MergeStrategy, SplitStrategy
from app.domain.intents.evolution.strategies.transition import TransitionStrategy

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class EvolutionStrategyRegistry:
    """
    Thread-safe registry for modular intent evolution strategies.
    """

    def __init__(self, register_defaults: bool = True):
        self._strategies: Dict[str, AbstractEvolutionStrategy] = {}
        self._lock = threading.RLock()

        if register_defaults:
            self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register core and standard domain strategies."""
        defaults: List[AbstractEvolutionStrategy] = [
            LifecycleStrategy(),
            TransitionStrategy(),
            ConfidenceStrategy(),
            MergeStrategy(),
            SplitStrategy(),
            CrossIndustryEvolutionStrategy(),
            RealEstateEvolutionStrategy(),
            HealthcareEvolutionStrategy(),
        ]
        for strat in defaults:
            self.register(strat)

    def register(self, strategy: AbstractEvolutionStrategy) -> None:
        """Register a new evolution strategy."""
        with self._lock:
            self._strategies[strategy.strategy_id] = strategy

    def unregister(self, strategy_id: str) -> Optional[AbstractEvolutionStrategy]:
        """Unregister a strategy by ID."""
        with self._lock:
            return self._strategies.pop(strategy_id, None)

    def get(self, strategy_id: str) -> Optional[AbstractEvolutionStrategy]:
        """Lookup a strategy by ID."""
        with self._lock:
            return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[AbstractEvolutionStrategy]:
        """Return all registered evolution strategies."""
        with self._lock:
            return list(self._strategies.values())

    def evaluate_all(self, context: IntentEvolutionContext) -> List[StrategyEvaluationResult]:
        """Execute all registered strategies sequentially against the evolution context."""
        results: List[StrategyEvaluationResult] = []
        with self._lock:
            strategies = list(self._strategies.values())

        for strat in strategies:
            res = strat.evaluate(context)
            results.append(res)
            context.strategies_evaluated_count += 1

        return results


default_evolution_strategy_registry = EvolutionStrategyRegistry()
