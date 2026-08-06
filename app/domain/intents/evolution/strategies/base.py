"""
HunterOS Engage V1 - Evolution Strategy Base
Abstract base class for modular evolution strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.evolution.models import (
    IntentEvolutionEvent,
    IntentStateTransition,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class StrategyEvaluationResult(BaseModel):
    """Container for artifacts emitted by an evolution strategy."""
    model_config = ConfigDict(frozen=True)

    events: List[IntentEvolutionEvent] = Field(default_factory=list)
    transitions: List[IntentStateTransition] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AbstractEvolutionStrategy(ABC):
    """
    Abstract base strategy governing intent evolution detection.
    Strategies are pure, deterministic, and free of ML or prediction.
    """

    def __init__(
        self,
        strategy_id: str,
        strategy_version: str = "1.0.0",
        description: str = "",
    ):
        self.strategy_id: str = strategy_id
        self.strategy_version: str = strategy_version
        self.description: str = description

    @abstractmethod
    def evaluate(self, context: IntentEvolutionContext) -> StrategyEvaluationResult:
        """Evaluate evolution conditions and emit events and transitions."""
        pass
