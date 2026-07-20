import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select

from app.domain.impact.models import ExecutiveImpactReport, ReportFrequency, ImpactCategory
from app.domain.impact.repository import ImpactRepository
from app.domain.impact.engines.narrative import ExecutiveNarrativeEngine
from app.domain.impact.engines.goals import GoalTrackingEngine
from app.domain.impact.engines.forecast import ForecastEngine

class ExecutiveReportingEngine:
    """
    Automates the generation of executive reports combining all engines.
    """

    @classmethod
    async def generate_report(
        cls, 
        repo: ImpactRepository, 
        workspace_id: uuid.UUID, 
        frequency: ReportFrequency
    ) -> ExecutiveImpactReport:
        
        end_date = datetime.now(timezone.utc)
        if frequency == ReportFrequency.WEEKLY:
            start_date = end_date - timedelta(days=7)
        elif frequency == ReportFrequency.MONTHLY:
            start_date = end_date - timedelta(days=30)
        elif frequency == ReportFrequency.QUARTERLY:
            start_date = end_date - timedelta(days=90)
        else:
            # ON_DEMAND defaults to last 30 days
            start_date = end_date - timedelta(days=30)
            
        attributions = await repo.get_attributions_for_period(workspace_id, start_date, end_date)
        
        # Aggregate data
        total_roi = sum(a.estimated_financial_value for a in attributions)
        hours_saved = sum(a.raw_metric_value for a in attributions if a.category == ImpactCategory.TIME_SAVINGS)
        rev_protected = sum(a.estimated_financial_value for a in attributions if a.category == ImpactCategory.REVENUE_PROTECTION)
        cost_reduction = sum(a.estimated_financial_value for a in attributions if a.category == ImpactCategory.COST_REDUCTION)
        
        forecast = ForecastEngine.generate_quarterly_forecast(attributions, (end_date - start_date).days)
        
        # Fetch current mocked state for goal tracking (would query other domains)
        current_kpis = {"lead_response_minutes": 27.0, "business_friction_score": 34.0}
        goals = await GoalTrackingEngine.evaluate_goals(repo, workspace_id, current_kpis)
        
        data_snapshot = {
            "overall_roi": total_roi,
            "hours_saved": hours_saved,
            "revenue_protected": rev_protected,
            "cost_reduction": cost_reduction,
            "forecast_quarterly_savings": forecast,
            "goals_status": goals,
            "top_risk": "Approvals delayed in Finance" # Mocked
        }
        
        narrative = ExecutiveNarrativeEngine.generate_narrative(data_snapshot)
        
        report = ExecutiveImpactReport(
            workspace_id=workspace_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            data_snapshot=data_snapshot,
            narrative_text=narrative
        )
        
        return await repo.save_executive_report(report)
