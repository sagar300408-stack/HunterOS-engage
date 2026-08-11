from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class BusinessValueRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        value_score = context.get('scores', {}).get('business_value')
        if value_score is None:
            return None
            
        value_level = "High" if value_score > 0.7 else "Medium" if value_score > 0.4 else "Low"
            
        return ExplanationSection(
            title="Business Value",
            content=f"The projected business value is {value_level} (Score: {value_score}).",
            evidence_refs=[]
        )
