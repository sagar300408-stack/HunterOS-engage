from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class UrgencyRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        urgency_score = context.get('scores', {}).get('urgency')
        if urgency_score is None:
            return None
            
        urgency_level = "Immediate" if urgency_score > 0.8 else "Soon" if urgency_score > 0.5 else "Flexible"
            
        return ExplanationSection(
            title="Urgency",
            content=f"Action is required: {urgency_level} (Score: {urgency_score}).",
            evidence_refs=[]
        )
