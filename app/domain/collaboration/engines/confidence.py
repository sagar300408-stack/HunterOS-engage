from typing import Tuple, List, Dict, Any
from app.domain.collaboration.models import ActionableIntent

class AIConfidenceEngine:
    """
    Evaluates the confidence score of the AI's ability to execute this intent based on available data.
    """

    @classmethod
    def evaluate(cls, intent: ActionableIntent, enriched_context: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Returns (confidence_score_between_0_and_1, list_of_confidence_factors).
        """
        score = 1.0
        factors = []
        
        # Example heuristic logic based on completeness of data
        if not enriched_context.get("customer_id"):
            score -= 0.3
            factors.append("Missing Customer ID")
            
        if intent.intent_type == "schedule_meeting":
            if not enriched_context.get("preferred_time"):
                score -= 0.4
                factors.append("Missing preferred time")
            else:
                factors.append("Preferred time identified")
                
            if enriched_context.get("agent_available", False):
                factors.append("Agent availability confirmed")
            else:
                score -= 0.2
                factors.append("Agent availability unknown")
                
        # Lower bound
        score = max(0.0, score)
        return score, factors
