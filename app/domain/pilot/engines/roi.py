from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import Dict, Any

from app.domain.pilot.models import PilotDeployment, PilotMetrics
from app.domain.roi.engines.calculator import ROICalculator

class PilotROIEngine:
    """
    Translates observed pilot metrics into executive-ready ROI case studies.
    """

    @staticmethod
    async def generate_executive_report(db: AsyncSession, pilot_id: uuid.UUID) -> Dict[str, Any]:
        """
        Aggregates Pilot metrics and utilizes the broader ROICalculator to generate the final
        executive validation report.
        """
        stmt = select(PilotDeployment).where(PilotDeployment.id == pilot_id)
        result = await db.execute(stmt)
        pilot = result.scalar_one_or_none()
        
        if not pilot:
            raise ValueError("Pilot not found")

        stmt_metrics = select(PilotMetrics).where(PilotMetrics.pilot_id == pilot_id).order_by(PilotMetrics.recorded_at.desc())
        result_metrics = await db.execute(stmt_metrics)
        latest_metrics = result_metrics.scalars().first()
        
        if not latest_metrics:
            return {"error": "Insufficient metrics to generate ROI report."}
            
        # Calculate reductions
        friction_reduction_pct = 0
        if latest_metrics.baseline_friction_score and latest_metrics.current_friction_score:
            diff = latest_metrics.baseline_friction_score - latest_metrics.current_friction_score
            friction_reduction_pct = (diff / latest_metrics.baseline_friction_score) * 100
            
        # In practice, we would call ROICalculator.calculate_impact() here using the workspace_id
        
        report = {
            "company": pilot.company_name,
            "executive_sponsor": pilot.executive_sponsor,
            "phase": pilot.phase,
            "metrics": {
                "business_friction_reduction_percentage": round(friction_reduction_pct, 1),
                "baseline_friction": latest_metrics.baseline_friction_score,
                "current_friction": latest_metrics.current_friction_score,
                "weekly_active_users": latest_metrics.weekly_active_users,
                "recommendation_acceptance_rate": latest_metrics.recommendation_acceptance_rate
            },
            "status": "Success" if friction_reduction_pct > 20 else "Needs Improvement"
        }
        return report
