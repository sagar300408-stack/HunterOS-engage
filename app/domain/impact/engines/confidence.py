from typing import List
from app.domain.impact.models import ImpactCategory, EvidenceTrace

class ROIConfidenceEngine:
    """
    Evaluates the certainty of an ROI claim based on the category and strength of evidence.
    """

    @classmethod
    def evaluate(cls, category: ImpactCategory, traces: List[EvidenceTrace]) -> float:
        """
        Returns a confidence score between 0.0 and 1.0.
        """
        base_confidence = 0.5
        
        # Hard metrics are highly confident
        if category in [ImpactCategory.TIME_SAVINGS, ImpactCategory.COST_REDUCTION]:
            base_confidence = 0.90
            
        # Predictive/estimated metrics are less confident
        elif category == ImpactCategory.REVENUE_PROTECTION:
            base_confidence = 0.60
            
        elif category == ImpactCategory.OPPORTUNITY_RECOVERY:
            base_confidence = 0.70
            
        # Boost confidence based on evidence chain length
        # (A longer, specific chain proves the outcome)
        evidence_boost = min(len(traces) * 0.05, 0.20)
        
        return min(base_confidence + evidence_boost, 1.0)
