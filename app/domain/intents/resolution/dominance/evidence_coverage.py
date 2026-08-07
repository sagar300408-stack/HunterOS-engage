"""
HunterOS Engage V1 - Evidence Coverage Dominance Strategy
Scores intents based on the volume and breadth of empirical evidence linked to them.
"""

from __future__ import annotations

from typing import Dict, List
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceEvaluationResult, DominanceStrategy
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


class EvidenceCoverageStrategy(DominanceStrategy):
    """
    Evaluates dominance based on evidence item count and distinct message spans.
    """

    def __init__(self, weight: float = 1.0) -> None:
        super().__init__(
            name="EvidenceCoverageStrategy",
            factor=DominanceFactor.EVIDENCE_COVERAGE,
            weight=weight,
        )

    def evaluate(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Dict[uuid.UUID, DominanceEvaluationResult]:
        if not candidates:
            return {}

        max_evidence = max((c.evidence_count or len(c.evidence_message_ids) or 1 for c in candidates), default=1)

        results: Dict[uuid.UUID, DominanceEvaluationResult] = {}
        for c in candidates:
            ev_count = max(c.evidence_count, len(c.evidence_message_ids))
            # Normalized score [0.0, 1.0]
            score = min(1.0, float(ev_count) / float(max_evidence)) if max_evidence > 0 else 0.5

            results[c.intent_id] = DominanceEvaluationResult(
                intent_id=c.intent_id,
                score=score,
                factor=self.factor,
                rationale=f"Evidence coverage: {ev_count} factual evidence points observed (relative max: {max_evidence})",
            )
        return results
