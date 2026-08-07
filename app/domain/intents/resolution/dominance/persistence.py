"""
HunterOS Engage V1 - Persistence Dominance Strategy
Scores intents based on chronological lifespan, lifecycle state, and historical persistence.
"""

from __future__ import annotations

from typing import Dict, List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceEvaluationResult, DominanceStrategy
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


class PersistenceStrategy(DominanceStrategy):
    """
    Evaluates dominance based on lifecycle stability and temporal span.
    """

    def __init__(self, weight: float = 1.0) -> None:
        super().__init__(
            name="PersistenceStrategy",
            factor=DominanceFactor.TIMELINE_PERSISTENCE,
            weight=weight,
        )

    def evaluate(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Dict[uuid.UUID, DominanceEvaluationResult]:
        if not candidates:
            return {}

        state_multipliers = {
            "PERSISTING": 1.0,
            "STRENGTHENING": 0.95,
            "ACTIVE": 0.8,
            "TRANSITIONED": 0.6,
            "NEW": 0.5,
            "WEAKENING": 0.4,
            "RESOLVED": 0.3,
            "CLOSED": 0.2,
        }

        results: Dict[uuid.UUID, DominanceEvaluationResult] = {}
        for c in candidates:
            multiplier = state_multipliers.get(c.lifecycle_state.upper(), 0.5)

            # Bonus for long temporal span if timestamps available
            span_bonus = 0.0
            if c.first_seen and c.last_seen and c.last_seen > c.first_seen:
                span_bonus = min(0.2, (c.last_seen - c.first_seen).total_seconds() / 86400.0)

            score = min(1.0, multiplier + span_bonus)

            results[c.intent_id] = DominanceEvaluationResult(
                intent_id=c.intent_id,
                score=score,
                factor=self.factor,
                rationale=f"Persistence score {score:.2f} based on lifecycle state '{c.lifecycle_state}' and historical timeline span",
            )
        return results
