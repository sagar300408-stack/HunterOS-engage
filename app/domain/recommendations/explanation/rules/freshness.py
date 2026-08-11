from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class FreshnessRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        freshness_score = context.get('scores', {}).get('freshness')
        if freshness_score is None:
            return None
            
        content = "This recommendation is based on recent data." if freshness_score > 0.7 else "This recommendation is based on older data."
            
        return ExplanationSection(
            title="Freshness",
            content=f"{content} (Score: {freshness_score}).",
            evidence_refs=[]
        )
