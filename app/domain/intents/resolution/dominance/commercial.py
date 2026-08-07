"""
HunterOS Engage V1 - Commercial Importance Dominance Strategy
Scores intents based on business domain importance and category weighting.
"""

from __future__ import annotations

from typing import Dict, List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceEvaluationResult, DominanceStrategy
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


class CommercialImportanceStrategy(DominanceStrategy):
    """
    Evaluates dominance based on business importance and commercial category.
    """

    def __init__(self, weight: float = 1.0) -> None:
        super().__init__(
            name="CommercialImportanceStrategy",
            factor=DominanceFactor.BUSINESS_IMPORTANCE,
            weight=weight,
        )

    def evaluate(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Dict[uuid.UUID, DominanceEvaluationResult]:
        if not candidates:
            return {}

        importance_scores = {
            "CRITICAL": 1.0,
            "HIGH": 0.85,
            "NORMAL": 0.6,
            "LOW": 0.35,
        }

        category_bonus = {
            "COMMERCIAL": 0.15,
            "OPERATIONAL": 0.05,
            "RELATIONSHIP": 0.0,
            "INFORMATION": -0.05,
        }

        results: Dict[uuid.UUID, DominanceEvaluationResult] = {}
        for c in candidates:
            base_score = importance_scores.get(c.business_importance.upper(), 0.5)
            bonus = category_bonus.get(c.category.upper(), 0.0)
            score = max(0.0, min(1.0, base_score + bonus))

            results[c.intent_id] = DominanceEvaluationResult(
                intent_id=c.intent_id,
                score=score,
                factor=self.factor,
                rationale=f"Business importance score {score:.2f} (importance: '{c.business_importance}', category: '{c.category}')",
            )
        return results
