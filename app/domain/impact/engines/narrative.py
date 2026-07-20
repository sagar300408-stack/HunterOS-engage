from typing import Dict, Any, List
from app.domain.impact.models import ValueAttribution, ImpactCategory

class ExecutiveNarrativeEngine:
    """
    Translates metric data into a plain-text executive briefing story.
    """

    @classmethod
    def generate_narrative(cls, data_snapshot: Dict[str, Any]) -> str:
        """
        Takes aggregated data and outputs the 'Executive Narrative'.
        """
        roi = data_snapshot.get("overall_roi", 0.0)
        hours = data_snapshot.get("hours_saved", 0.0)
        
        narrative = []
        narrative.append(f"This period, HunterOS generated an estimated ₹{roi:,.2f} in financial value.")
        narrative.append(f"Automation eliminated {hours:,.1f} hours of manual effort.")
        
        # Determine biggest improvement
        if data_snapshot.get("revenue_protected", 0.0) > data_snapshot.get("cost_reduction", 0.0):
            narrative.append("The biggest driver of ROI was Revenue Protection from recovered opportunities and SLA compliance.")
        else:
            narrative.append("The biggest driver of ROI was direct Cost Reduction through automation.")
            
        # Top risk/bottleneck (would come from intelligence engine, placeholder here)
        top_risk = data_snapshot.get("top_risk")
        if top_risk:
            narrative.append(f"The largest remaining bottleneck is: {top_risk}.")
            
        return " ".join(narrative)
