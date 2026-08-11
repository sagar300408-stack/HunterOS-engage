from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class PriorityRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        priority_score = context.get('scores', {}).get('priority')
        if priority_score is None:
            return None
            
        priority_level = "High" if priority_score > 0.7 else "Medium" if priority_score > 0.4 else "Low"
            
        return ExplanationSection(
            title="Priority",
            content=f"This recommendation has a {priority_level} priority (Score: {priority_score}).",
            evidence_refs=[]
        )
