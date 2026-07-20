from typing import Any

class ContextConfidenceEngine:
    """
    Scores the reliability of a context entity based on its source and verification history.
    """

    @classmethod
    def evaluate(cls, entity: Any) -> float:
        """
        Dynamically adjusts the static confidence_score of an entity based on heuristics.
        """
        score = getattr(entity, 'confidence_score', 1.0)
        source = getattr(entity, 'source_system', 'UNKNOWN')
        
        # Example heuristic: INFERENCE is less confident than a CRM
        if source == "INFERENCE_ENGINE":
            score *= 0.7
            
        elif source == "MANUAL_ENTRY":
            score *= 0.95
            
        return round(score, 2)
