from typing import List, Dict, Any
import uuid

from app.domain.impact.repository import ImpactRepository
from app.domain.impact.models import BusinessTargets

class GoalTrackingEngine:
    """
    Compares current operational metrics against configured business targets.
    """

    @classmethod
    async def evaluate_goals(cls, repo: ImpactRepository, workspace_id: uuid.UUID, current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Returns a list of goal evaluations.
        """
        targets = await repo.get_business_targets(workspace_id)
        results = []
        
        for target in targets:
            current_val = current_metrics.get(target.kpi_name, 0.0)
            
            # Simple condition parsing
            achieved = False
            if target.condition == "<=" and current_val <= target.target_value:
                achieved = True
            elif target.condition == ">=" and current_val >= target.target_value:
                achieved = True
                
            results.append({
                "kpi_name": target.kpi_name,
                "target_value": target.target_value,
                "current_value": current_val,
                "status": "Achieved" if achieved else "Behind Target"
            })
            
        return results
