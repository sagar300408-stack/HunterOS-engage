from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class ConfidenceRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        confidence_score = context.get('scores', {}).get('confidence')
        if confidence_score is None:
            return None
            
        confidence_level = "High" if confidence_score > 0.85 else "Moderate" if confidence_score > 0.5 else "Low"
            
        return ExplanationSection(
            title="Confidence",
            content=f"System confidence in this recommendation is {confidence_level} (Score: {confidence_score}).",
            evidence_refs=[]
        )
