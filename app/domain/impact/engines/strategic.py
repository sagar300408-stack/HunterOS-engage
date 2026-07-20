from typing import List, Dict, Any
from app.domain.impact.models import ValueAttribution, ImpactCategory

class StrategicImpactEngine:
    """
    Summarizes intangible or long-term strategic improvements.
    """

    @classmethod
    def evaluate(cls, attributions: List[ValueAttribution]) -> Dict[str, Any]:
        """
        Provides qualitative insights based on the mix of impact categories.
        """
        strategic_count = sum(1 for a in attributions if a.category == ImpactCategory.STRATEGIC)
        total = len(attributions)
        
        insight = "Operational stability is maintained."
        if total > 0:
            if strategic_count > 5:
                insight = "High cross-team collaboration and strategic improvements detected."
                
        return {
            "strategic_events_logged": strategic_count,
            "executive_insight": insight
        }
