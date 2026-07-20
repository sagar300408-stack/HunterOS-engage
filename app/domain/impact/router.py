import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.integrations.postgres.database import get_db
from app.domain.impact.schemas import (
    FinancialConfigResponse,
    BusinessTargetResponse,
    BaselineMetricResponse,
    ValueAttributionSchema,
    ImpactSummaryResponse,
    ExecutiveReportResponse
)
from app.domain.impact.repository import ImpactRepository
from app.domain.impact.engines.reporting import ExecutiveReportingEngine
from app.domain.impact.models import ReportFrequency, ImpactCategory
from app.domain.impact.engines.forecast import ForecastEngine
from app.domain.impact.engines.goals import GoalTrackingEngine
from app.domain.impact.engines.narrative import ExecutiveNarrativeEngine

router = APIRouter(prefix="/impact", tags=["Impact"])

@router.get("/summary", response_model=ImpactSummaryResponse)
async def get_impact_summary(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = ImpactRepository(db)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    attributions = await repo.get_attributions_for_period(workspace_id, start_date, end_date)
    
    total_roi = sum(a.estimated_financial_value for a in attributions)
    hours_saved = sum(a.raw_metric_value for a in attributions if a.category == ImpactCategory.TIME_SAVINGS)
    rev_protected = sum(a.estimated_financial_value for a in attributions if a.category == ImpactCategory.REVENUE_PROTECTION)
    cost_reduction = sum(a.estimated_financial_value for a in attributions if a.category == ImpactCategory.COST_REDUCTION)
    
    forecast = ForecastEngine.generate_quarterly_forecast(attributions, 30)
    
    # Mocking current KPI states for dashboard
    current_kpis = {"lead_response_minutes": 15.0, "business_friction_score": 12.0}
    goals = await GoalTrackingEngine.evaluate_goals(repo, workspace_id, current_kpis)
    
    data_snapshot = {
        "overall_roi": total_roi,
        "hours_saved": hours_saved,
        "revenue_protected": rev_protected,
        "cost_reduction": cost_reduction,
        "forecast_quarterly_savings": forecast,
        "goals_status": goals,
        "top_risk": "None"
    }
    
    narrative = ExecutiveNarrativeEngine.generate_narrative(data_snapshot)
    
    return ImpactSummaryResponse(
        overall_roi=total_roi,
        currency="INR",
        revenue_protected=rev_protected,
        cost_reduction=cost_reduction,
        hours_saved=hours_saved,
        business_friction_score=12.0,
        operational_health_index=88.5,
        forecast_quarterly_savings=forecast,
        executive_narrative=narrative,
        goals_status=goals,
        top_recommendation="Expand automation to Finance department",
        top_risk="Pending approvals queue"
    )

@router.get("/reports", response_model=List[ExecutiveReportResponse])
async def list_reports(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = ImpactRepository(db)
    return await repo.list_reports(workspace_id)

@router.post("/reports/generate", response_model=ExecutiveReportResponse)
async def generate_report(workspace_id: uuid.UUID, frequency: ReportFrequency, db: AsyncSession = Depends(get_db)):
    repo = ImpactRepository(db)
    return await ExecutiveReportingEngine.generate_report(repo, workspace_id, frequency)
