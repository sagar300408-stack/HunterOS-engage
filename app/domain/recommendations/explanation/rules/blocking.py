from typing import Any, Dict, Optional
from .base import AbstractRecommendationExplanationRule, ExplanationSection

class BlockingRule(AbstractRecommendationExplanationRule):
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        is_blocking = context.get('attributes', {}).get('is_blocking', False)
        if not is_blocking:
            return None
            
        blocked_items = context.get('attributes', {}).get('blocked_items', [])
        content = "This recommendation is blocking other actions."
        if blocked_items:
            content += f" Blocks: {', '.join(blocked_items)}."
            
        return ExplanationSection(
            title="Blocking Status",
            content=content,
            evidence_refs=[]
        )
