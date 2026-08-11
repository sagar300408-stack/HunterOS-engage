from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class ImpactRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        impact_score = context.get('scores', {}).get('impact')
        if impact_score is None:
            return None
            
        impact_level = "Significant" if impact_score > 0.75 else "Moderate" if impact_score > 0.4 else "Minor"
            
        return ExplanationSection(
            title="Impact",
            content=f"The expected impact is {impact_level} (Score: {impact_score}).",
            evidence_refs=[]
        )
