from typing import List, Optional
from uuid import UUID

from app.domain.briefing.templates.base import BaseBriefingTemplate
from app.domain.briefing.schemas import BriefingCalculationResult
from app.domain.insight.repository import InsightRepository
from app.domain.recommendation.repository import RecommendationRepository
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository


class BriefingComposer:
    """
    Composes Executive Briefings deterministically by feeding current intelligence snapshots
    into a designated template.
    """
    def __init__(
        self, 
        insight_repo: InsightRepository, 
        recommendation_repo: RecommendationRepository,
        health_repo: HealthRepository,
        kpi_repo: KpiRepository
    ):
        self.insight_repo = insight_repo
        self.recommendation_repo = recommendation_repo
        self.health_repo = health_repo
        self.kpi_repo = kpi_repo
        
    async def compose_briefing(self, workspace_id: UUID, template: BaseBriefingTemplate) -> BriefingCalculationResult:
        # 1. Fetch current active intelligence state
        kpis = await self.kpi_repo.get_latest_kpis(workspace_id, limit=50)
        health_snapshots = await self.health_repo.get_latest_health(workspace_id, limit=20)
        insights = await self.insight_repo.get_latest_insights("workspace", workspace_id, limit=50)
        recommendations = await self.recommendation_repo.get_latest_recommendations("workspace", workspace_id, limit=50)
        
        # 2. Hand off raw data to the template for composition, filtering, and prioritization
        result = template.compose(insights, recommendations, health_snapshots, kpis)
        
        return result
