from . import PipelineStage
from typing import Dict, Any

class CalculatePriorityStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        for candidate in state["candidates"]:
            total_score = 0.0
            total_weight = 0.0
            for factor_res in getattr(candidate, "factors", {}).values():
                total_score += factor_res.score * factor_res.weight
                total_weight += factor_res.weight
            candidate.final_score = (total_score / total_weight * 100) if total_weight > 0 else 0
            
            if candidate.final_score >= 80:
                candidate.priority_level = "HIGH"
            elif candidate.final_score >= 50:
                candidate.priority_level = "MEDIUM"
            else:
                candidate.priority_level = "LOW"
        return state
