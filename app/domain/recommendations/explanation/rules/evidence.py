from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class EvidenceRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        evidence = context.get('evidence', [])
        if not evidence:
            return None
            
        content = "The recommendation is supported by the following evidence:\\n"
        for item in evidence:
            content += f"- {item.get('description', 'Unknown')}\\n"
            
        return ExplanationSection(
            title="Supporting Evidence",
            content=content,
            evidence_refs=[item.get('id') for item in evidence if item.get('id')]
        )
