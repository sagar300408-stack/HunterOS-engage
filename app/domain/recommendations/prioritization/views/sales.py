from typing import List, Dict, Any
from ..models import RecommendationPrioritizationResult, PriorityFactorType

class SalesView:
    @staticmethod
    def generate(result: RecommendationPrioritizationResult) -> List[Dict[str, Any]]:
        # Focus on business value and strategic alignment
        sales_focused = []
        for rec in result.recommendations:
            business_value_score = next((f.score for f in rec.assessment.score.factors if f.factor_type == PriorityFactorType.BUSINESS_VALUE), 0)
            if business_value_score > 50:
                sales_focused.append({
                    "candidate_id": rec.candidate.candidate_id,
                    "rank": rec.rank,
                    "business_value_score": business_value_score
                })
        return sales_focused
