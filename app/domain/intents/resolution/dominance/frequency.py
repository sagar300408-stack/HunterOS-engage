"""
HunterOS Engage V1 - Frequency Dominance Strategy
Scores intents based on conversation occurrence count and recurrence rate across interactions.
"""

from __future__ import annotations

from typing import Dict, List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceEvaluationResult, DominanceStrategy
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


class FrequencyStrategy(DominanceStrategy):
    """
    Evaluates dominance based on the frequency of conversation appearances.
    """

    def __init__(self, weight: float = 1.0) -> None:
        super().__init__(
            name="FrequencyStrategy",
            factor=DominanceFactor.CONVERSATION_FREQUENCY,
            weight=weight,
        )

    def evaluate(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Dict[uuid.UUID, DominanceEvaluationResult]:
        if not candidates:
            return {}

        max_convs = max((len(c.source_conversations) or 1 for c in candidates), default=1)

        results: Dict[uuid.UUID, DominanceEvaluationResult] = {}
        for c in candidates:
            conv_count = len(c.source_conversations) or 1
            score = min(1.0, float(conv_count) / float(max_convs)) if max_convs > 0 else 0.5

            results[c.intent_id] = DominanceEvaluationResult(
                intent_id=c.intent_id,
                score=score,
                factor=self.factor,
                rationale=f"Frequency score {score:.2f} across {conv_count} observed conversation threads",
            )
        return results
