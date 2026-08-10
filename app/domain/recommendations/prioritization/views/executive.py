from typing import Dict, Any
from ..models import RecommendationPrioritizationResult

class ExecutiveView:
    @staticmethod
    def generate(result: RecommendationPrioritizationResult) -> Dict[str, Any]:
        total = len(result.recommendations)
        distribution = {}
        for rec in result.recommendations:
            level = rec.assessment.score.level.value
            distribution[level] = distribution.get(level, 0) + 1
            
        return {
            "total_recommendations": total,
            "priority_distribution": distribution
        }
