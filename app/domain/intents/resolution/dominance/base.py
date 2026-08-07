"""
HunterOS Engage V1 - Dominance Strategy Base
Defines the strategy pattern for evaluating descriptive intent dominance within resolution groups.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


class DominanceEvaluationResult(BaseModel):
    """Evaluation score and rationale produced by an individual dominance strategy."""
    model_config = ConfigDict(frozen=True)

    intent_id: uuid.UUID
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    factor: Any
    rationale: str = ""


class DominanceStrategy(ABC):
    """
    Abstract base class for deterministic dominance calculation strategies.
    Evaluates candidates purely from historical observation and factual metrics.
    """

    def __init__(self, name: str, factor: Any, weight: float = 1.0) -> None:
        self.name: str = name
        self.factor: Any = factor
        self.weight: float = max(0.0, weight)

    @abstractmethod
    def evaluate(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Dict[uuid.UUID, DominanceEvaluationResult]:
        """
        Evaluate candidate intent nodes and return a mapping of intent_id -> DominanceEvaluationResult.
        """
        pass
