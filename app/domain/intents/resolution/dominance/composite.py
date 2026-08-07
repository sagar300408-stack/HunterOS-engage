"""
HunterOS Engage V1 - Composite Dominance Strategy
Combines multiple pluggable dominance strategies into a holistic deterministic dominance ranking.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.base import DominanceEvaluationResult, DominanceStrategy
from app.domain.intents.resolution.dominance.commercial import CommercialImportanceStrategy
from app.domain.intents.resolution.dominance.evidence_coverage import EvidenceCoverageStrategy
from app.domain.intents.resolution.dominance.frequency import FrequencyStrategy
from app.domain.intents.resolution.dominance.persistence import PersistenceStrategy
from app.domain.intents.resolution.models import DominanceFactor, DominantIntent, IntentNode


class CompositeDominanceStrategy:
    """
    Evaluates a pool of candidate IntentNodes within a group across multiple strategies,
    computing composite scores and electing the descriptive DominantIntent.
    """

    def __init__(self, strategies: Optional[List[DominanceStrategy]] = None) -> None:
        self.strategies: List[DominanceStrategy] = strategies or [
            EvidenceCoverageStrategy(weight=1.5),
            CommercialImportanceStrategy(weight=1.2),
            PersistenceStrategy(weight=1.0),
            FrequencyStrategy(weight=0.8),
        ]

    def resolve_dominant_intent(
        self,
        candidates: List[IntentNode],
        context: MultiIntentResolutionContext,
    ) -> Optional[DominantIntent]:
        """
        Evaluate candidate intent nodes and elect the dominant intent.
        """
        if not candidates:
            return None

        if len(candidates) == 1:
            node = candidates[0]
            return DominantIntent(
                intent_id=node.intent_id,
                canonical_name=node.canonical_name,
                dominance_score=1.0,
                primary_factor=DominanceFactor.EVIDENCE_COVERAGE,
                supporting_factors={"EVIDENCE_COVERAGE": 1.0},
                rationale="Single intent in group; inherently dominant.",
                supporting_intent_ids=[],
            )

        context.strategies_evaluated_count += len(self.strategies)

        strategy_results: Dict[str, Dict[uuid.UUID, DominanceEvaluationResult]] = {}
        total_weight = sum(s.weight for s in self.strategies) or 1.0

        for s in self.strategies:
            strategy_results[s.name] = s.evaluate(candidates, context)

        # Aggregate weighted scores per candidate
        candidate_scores: Dict[uuid.UUID, float] = {}
        factor_breakdown: Dict[uuid.UUID, Dict[str, float]] = {}
        best_factors: Dict[uuid.UUID, DominanceFactor] = {}

        for c in candidates:
            weighted_sum = 0.0
            breakdown: Dict[str, float] = {}
            top_factor_score = -1.0
            top_factor = DominanceFactor.EVIDENCE_COVERAGE

            for s in self.strategies:
                res = strategy_results.get(s.name, {}).get(c.intent_id)
                score = res.score if res else 0.5
                weighted_sum += score * s.weight
                breakdown[s.factor.value] = round(score, 3)

                if score > top_factor_score:
                    top_factor_score = score
                    top_factor = s.factor

            candidate_scores[c.intent_id] = weighted_sum / total_weight
            factor_breakdown[c.intent_id] = breakdown
            best_factors[c.intent_id] = top_factor

        # Select candidate with highest composite score
        best_candidate = max(candidates, key=lambda c: (candidate_scores.get(c.intent_id, 0.0), c.confidence))
        best_id = best_candidate.intent_id
        best_score = round(candidate_scores.get(best_id, 1.0), 3)
        primary_factor = best_factors.get(best_id, DominanceFactor.EVIDENCE_COVERAGE)
        supporting_ids = [c.intent_id for c in candidates if c.intent_id != best_id]

        rationale = (
            f"Elected '{best_candidate.canonical_name}' with composite score {best_score} "
            f"(primary driver: {primary_factor.value}, supporting factors: {factor_breakdown.get(best_id, {})})"
        )

        return DominantIntent(
            intent_id=best_id,
            canonical_name=best_candidate.canonical_name,
            dominance_score=best_score,
            primary_factor=primary_factor,
            supporting_factors=factor_breakdown.get(best_id, {}),
            rationale=rationale,
            supporting_intent_ids=supporting_ids,
        )
