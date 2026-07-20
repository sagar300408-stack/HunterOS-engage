from typing import Tuple, List
from app.domain.collaboration.models import AutonomyLevel, RiskLevel

class TaskOwnershipEngine:
    """
    Makes the final determination on who owns the task (AI or Human) 
    by combining Autonomy Policy, Risk Level, Exceptions, and Confidence.
    """

    CONFIDENCE_THRESHOLD = 0.85

    @classmethod
    def evaluate(
        cls, 
        has_exception: bool, 
        base_autonomy: AutonomyLevel, 
        risk_level: RiskLevel, 
        confidence: float
    ) -> Tuple[AutonomyLevel, List[str]]:
        """
        Returns (FinalAutonomyLevel, list_of_decision_reasons).
        """
        reasons = []

        # 1. Hard Stops
        if has_exception:
            reasons.append("Exception detected: Forcing HUMAN_OWNED.")
            return AutonomyLevel.HUMAN_OWNED, reasons
            
        if risk_level == RiskLevel.CRITICAL:
            reasons.append("CRITICAL risk level: Forcing HUMAN_OWNED.")
            return AutonomyLevel.HUMAN_OWNED, reasons

        # 2. Confidence Checks
        if confidence < cls.CONFIDENCE_THRESHOLD:
            reasons.append(f"AI Confidence ({confidence}) below threshold ({cls.CONFIDENCE_THRESHOLD}).")
            if base_autonomy == AutonomyLevel.AI_OWNED:
                reasons.append("Downgrading from AI_OWNED to HUMAN_REVIEW.")
                return AutonomyLevel.HUMAN_REVIEW, reasons
                
        # 3. Risk Escalations
        if risk_level == RiskLevel.HIGH and base_autonomy == AutonomyLevel.AI_OWNED:
             reasons.append("HIGH risk level: Downgrading AI_OWNED to HUMAN_REVIEW.")
             return AutonomyLevel.HUMAN_REVIEW, reasons

        reasons.append(f"Retaining policy autonomy level: {base_autonomy.value}.")
        return base_autonomy, reasons
