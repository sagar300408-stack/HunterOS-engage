from typing import List, Dict, Any
from ..models import RecommendationPrioritizationResult

class AuditView:
    @staticmethod
    def generate(result: RecommendationPrioritizationResult) -> List[Dict[str, Any]]:
        # Full factor and evidence traceability
        audit_trail = []
        for rec in result.recommendations:
            factors_trace = []
            for factor in rec.assessment.score.factors:
                factors_trace.append({
                    "factor_type": factor.factor_type.value,
                    "score": factor.score,
                    "weight": factor.weight,
                    "evidence": factor.evidence,
                    "strength": factor.strength.value
                })
            
            audit_trail.append({
                "candidate_id": rec.candidate.candidate_id,
                "assessed_at": rec.assessment.assessed_at.isoformat(),
                "assessor_id": rec.assessment.assessor_id,
                "method": rec.assessment.method.value,
                "factors_traceability": factors_trace
            })
        return audit_trail
