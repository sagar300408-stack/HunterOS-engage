from typing import Any, Dict, Optional
from ..base import AbstractRecommendationExplanationRule, ExplanationSection

class HealthcareIndustryRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        industry = context.get('industry')
        if industry != 'healthcare':
            return None
            
        compliance = context.get('attributes', {}).get('compliance_required', False)
        content = "This recommendation aligns with Healthcare industry standards."
        if compliance:
            content += " It includes necessary compliance checks."
            
        return ExplanationSection(
            title="Healthcare Context",
            content=content,
            evidence_refs=[]
        )
