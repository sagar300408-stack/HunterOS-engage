from typing import Any, Dict, Optional
from ..base import AbstractRecommendationExplanationRule, ExplanationSection

class RealEstateIndustryRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        industry = context.get('industry')
        if industry != 'real_estate':
            return None
            
        property_type = context.get('attributes', {}).get('property_type', 'unknown')
        return ExplanationSection(
            title="Real Estate Context",
            content=f"This recommendation is tailored for the Real Estate sector, specifically for {property_type} properties.",
            evidence_refs=[]
        )
