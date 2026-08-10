from typing import List, Dict, Any
from ..models import RecommendationPrioritizationResult, PriorityFactorType

class OperationsView:
    @staticmethod
    def generate(result: RecommendationPrioritizationResult) -> List[Dict[str, Any]]:
        # Focus on blockers and risk mitigation
        ops_focused = []
        for rec in result.recommendations:
            risk_mitigation_score = next((f.score for f in rec.assessment.score.factors if f.factor_type == PriorityFactorType.RISK_MITIGATION), 0)
            ops_focused.append({
                "candidate_id": rec.candidate.candidate_id,
                "urgency": rec.assessment.score.urgency.value,
                "risk_mitigation_score": risk_mitigation_score
            })
        return ops_focused
