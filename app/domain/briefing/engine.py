import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.briefing.repository import BriefingRepository
from app.domain.briefing.composer import BriefingComposer
from app.domain.briefing.models import BriefingSnapshot, BriefingPeriod
from app.domain.briefing.templates.registry import briefing_registry
from app.domain.insight.repository import InsightRepository
from app.domain.recommendation.repository import RecommendationRepository
from app.domain.health.repository import HealthRepository
from app.domain.kpi.repository import KpiRepository


logger = logging.getLogger(__name__)


class ExecutiveBriefingEngine:
    """
    Engine responsible for orchestrating the generation of Executive Briefings.
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.briefing_repo = BriefingRepository(session)
        
        self.composer = BriefingComposer(
            insight_repo=InsightRepository(session),
            recommendation_repo=RecommendationRepository(session),
            health_repo=HealthRepository(session),
            kpi_repo=KpiRepository(session)
        )
        
    async def generate_briefing(self, workspace_id: UUID, template_name: str, period: str = BriefingPeriod.ON_DEMAND.value) -> BriefingSnapshot:
        template = briefing_registry.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found in registry.")
            
        try:
            # 1. Compose Briefing
            result = await self.composer.compose_briefing(workspace_id, template)
            
            # 2. Construct Snapshot
            snapshot = BriefingSnapshot(
                workspace_id=workspace_id,
                template_name=template_name,
                period=period,
                executive_summary=result.executive_summary,
                kpi_summary=result.kpi_summary,
                health_summary=result.health_summary,
                key_insights=result.key_insights,
                priority_recommendations=result.priority_recommendations,
                critical_risks=result.critical_risks,
                business_opportunities=result.business_opportunities,
                supporting_references=result.supporting_references,
                confidence=result.confidence
            )
            
            # 3. Save and Return
            saved_snapshot = await self.briefing_repo.save_briefing(snapshot)
            return saved_snapshot
            
        except Exception as e:
            logger.error(f"Failed to generate briefing using {template_name}: {e}")
            raise
